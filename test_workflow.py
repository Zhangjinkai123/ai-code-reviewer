import importlib
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parent


def load_workflow(filename):
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
    )


def prepare_report(main, directory, issues):
    """运行 CLI 的实际审查、定位、落盘和门禁，仅替换外部输入和模型服务。"""
    diff = (ROOT / "examples/yaml_regression_invalid.diff").read_text(encoding="utf-8")
    response = SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=json.dumps({"issues": issues})))
    ])
    shutil.copyfile(ROOT / "review.yaml", directory / "review.yaml")
    original_directory = Path.cwd()
    try:
        os.chdir(directory)
        with patch.object(main, "get_git_diff", return_value=diff), patch(
            "reviewer.analyzer.client.chat.completions.create",
            return_value=response,
        ), patch.object(sys, "argv", ["main.py", "review"]), redirect_stdout(io.StringIO()):
            try:
                main.main()
                exit_code = 0
            except SystemExit as exc:
                exit_code = exc.code
        report = directory / "reports/review-report.json"
        assert report.exists()
        result = json.loads(report.read_text(encoding="utf-8"))
        assert len(result["issues"]) == len(issues)
        if issues:
            assert result["issues"][0]["line"] == "19"
        return exit_code
    finally:
        os.chdir(original_directory)


def test_dual_workflow_contract():
    """使用工作流原始评论脚本验证成功、门禁失败和乱序独立评论。"""
    fake_settings = SimpleNamespace(
        OPENAI_API_KEY="test-placeholder",
        OPENAI_BASE_URL="https://example.invalid/v1",
        LLM_MODEL="test-model",
    )
    with patch.dict(sys.modules, {"config": SimpleNamespace(settings=fake_settings)}):
        verify_dual_workflow_contract()


def verify_dual_workflow_contract():
    upstream = load_workflow("ai-review.yml")
    downstream = load_workflow("ai-review-comment.yml")
    upload = next(
        step for step in upstream["jobs"]["review"]["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload["if"] == "always()"
    assert upload["with"]["name"] == "ai-review-result"
    assert upload["with"]["path"] == "reports/review-report.json"
    comment_steps = downstream["jobs"]["comment"]["steps"]
    checkout = next(
        step for step in comment_steps
        if step.get("uses", "").startswith("actions/checkout@")
    )
    assert "ref" not in checkout.get("with", {})
    download = next(
        step for step in comment_steps
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    assert download["with"]["run-id"] == "${{ github.event.workflow_run.id }}"
    assert download["with"]["name"] == upload["with"]["name"]
    assert downstream["permissions"]["actions"] == "read"
    assert "'failure'" in downstream["jobs"]["comment"]["if"]
    comment_step = next(step for step in comment_steps if step["name"] == "Create PR Comment")
    assert comment_step["env"]["COMMIT_SHA"] == "${{ github.event.workflow_run.head_sha }}"
    assert comment_step["env"]["REVIEW_RUN_ID"] == "${{ github.event.workflow_run.id }}"
    command = shlex.split(comment_step["run"])
    assert command[:2] == ["python", "-c"]
    assert len(command) == 3
    source = compile(command[2], "<workflow-comment-script>", "exec")

    main = importlib.import_module("main")
    issue = {
        "file": ".github/workflows/test.yml",
        "code_snippet": "COMMIT_SHA: ${{ github.event.workflow_run.head_sha }}",
        "severity": "high",
        "category": "configuration",
        "message": "步骤包含无效字段",
        "suggestion": "将变量移入 env",
    }
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        failed = root / "failed"
        passed = root / "passed"
        failed.mkdir()
        passed.mkdir()
        assert prepare_report(main, failed, [issue]) == 1
        assert prepare_report(main, passed, []) == 0
        original_directory = Path.cwd()
        try:
            with patch("reviewer.commenter.post_pr_comment") as post:
                post.return_value = {"html_url": "https://example.invalid/comment"}
                # 新 Run 先完成、旧 Run 后完成，随后同一提交重跑；每次均应独立发布。
                cases = [
                    (passed, "b" * 40, 202),
                    (failed, "a" * 40, 101),
                    (failed, "a" * 40, 303),
                ]
                for directory, sha, run_id in cases:
                    destination = directory / "review-result"
                    destination.mkdir(exist_ok=True)
                    shutil.copyfile(
                        directory / "reports/review-report.json",
                        destination / "review-report.json",
                    )
                    os.chdir(directory)
                    with patch.dict(os.environ, {
                        "GITHUB_REPOSITORY": "owner/repository",
                        "PR_NUMBER": "9",
                        "GITHUB_TOKEN": "test-token",
                        "COMMIT_SHA": sha,
                        "REVIEW_RUN_ID": str(run_id),
                    }):
                        exec(source, {"__name__": "__main__"})
                    body = post.call_args.kwargs["body"]
                    assert sha in body
                    assert f"/actions/runs/{run_id}" in body
                    if directory == failed:
                        assert "#L19" in body
                        assert "No issues found" not in body
                    else:
                        assert "No issues found" in body
                assert post.call_count == 3
                assert "b" * 40 in post.call_args_list[0].kwargs["body"]
                assert "a" * 40 not in post.call_args_list[0].kwargs["body"]
        finally:
            os.chdir(original_directory)
    print("Dual workflow integration assertions passed.")


if __name__ == "__main__":
    test_dual_workflow_contract()
