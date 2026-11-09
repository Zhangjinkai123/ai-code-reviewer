import importlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from reviewer.commenter import create_pr_comment, load_review_result
from reviewer.policy import check_policy, load_policy
from reviewer.reporter import save_report


def test_review_pipeline():
    """模拟服务响应，覆盖实际解析、模型校验和行号定位。"""
    fake_settings = SimpleNamespace(
        OPENAI_API_KEY="test-placeholder",
        OPENAI_BASE_URL="https://example.invalid/v1",
        LLM_MODEL="test-model",
    )
    with patch.dict(sys.modules, {"config": SimpleNamespace(settings=fake_settings)}):
        analyzer = importlib.import_module("reviewer.analyzer")

    diff = Path("examples/yaml_regression_invalid.diff").read_text(encoding="utf-8")
    issue = {
        "file": ".github/workflows/test.yml",
        "code_snippet": "COMMIT_SHA: ${{ github.event.workflow_run.head_sha }}",
        "severity": "high",
        "category": "configuration",
        "message": "步骤字段无效",
        "suggestion": "将变量放入 env",
    }
    with patch.object(analyzer.client.chat.completions, "create") as create:
        create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content=json.dumps({"issues": [issue]})))
        ])
        result = analyzer.review_code(diff)
        assert result.issues[0].line == "19"
        # 模拟 Artifact 落盘后由独立评论流程读取，门禁失败仍可发布评论。
        assert check_policy(result, load_policy()) is False
        with tempfile.TemporaryDirectory() as directory:
            report = str(Path(directory) / "review-report.json")
            save_report(result, report)
            assert load_review_result(report) == result
            with patch("reviewer.commenter.post_pr_comment") as post:
                create_pr_comment(
                    report, "owner/repository", 9, "test-token", "a" * 40,
                    run_id=123456,
                )
                body = post.call_args.kwargs["body"]
                assert "COMMIT_SHA" in body
                assert "a" * 40 in body
                assert "#L19" in body
                assert "/actions/runs/123456" in body
        sent = json.loads(create.call_args.kwargs["messages"][1]["content"])
        assert sent[0]["yaml_context"]["complete"] is True
        assert any(
            item["path"] == "$.jobs.comment.steps[0].COMMIT_SHA"
            for item in sent[0]["yaml_context"]["key_paths"]
        )

        for content, error_type in (
            ('{"issues": []}', None),
            ('{"issues": [{"severity": "high"}]}', ValidationError),
            ("not json", json.JSONDecodeError),
        ):
            create.return_value.choices[0].message.content = content
            if error_type is None:
                assert analyzer.review_code(diff).issues == []
            else:
                try:
                    analyzer.review_code(diff)
                except error_type:
                    pass
                else:
                    raise AssertionError("未拒绝无效模型响应")
    print("Analyzer pipeline assertions passed.")


def run_live_review(sample: str):
    """按需使用项目配置做真实模型验收，不输出配置和异常正文。"""
    from reviewer import analyzer
    from reviewer.reporter import save_report

    samples = {
        "valid": "yaml_regression_valid.diff",
        "invalid": "yaml_regression_invalid.diff",
        "sql": "bad_code.diff",
    }
    diff = (Path("examples") / samples[sample]).read_text(encoding="utf-8")
    with patch.object(
        analyzer,
        "client",
        analyzer.client.with_options(timeout=90, max_retries=0),
    ):
        try:
            result = analyzer.review_code(diff)
        except Exception as exc:
            print(f"Live review failed: {type(exc).__name__}")
            return 1

    save_report(result, f"reports/live-{sample}.json")
    print(result.model_dump_json(indent=2))
    if sample == "valid":
        passed = not result.issues
    elif sample == "invalid":
        passed = any(
            "COMMIT_SHA" in (issue.code_snippet or "")
            and issue.line is not None
            for issue in result.issues
        )
    else:
        passed = any(
            ("sql" in issue.category.lower() or "注入" in issue.message.lower())
            and issue.line is not None
            for issue in result.issues
        )
    print(f"Live {sample}: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--live":
        raise SystemExit(run_live_review(sys.argv[2]))
    test_review_pipeline()
