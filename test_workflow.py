import importlib
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import re
import shlex
import shutil
import subprocess
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


def load_workflow_strings(filename):
    return yaml.load(
        (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def collect_action_references(value):
    if isinstance(value, dict):
        references = []
        for key, child in value.items():
            if key == "uses" and isinstance(child, str):
                references.append(child)
            else:
                references.extend(collect_action_references(child))
        return references
    if isinstance(value, list):
        return [
            reference
            for child in value
            for reference in collect_action_references(child)
        ]
    return []


def test_actions_are_pinned_to_full_commit_sha():
    files = [ROOT / "action.yml", *(ROOT / ".github" / "workflows").glob("*.yml")]
    references = []
    for path in files:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        references.extend(collect_action_references(data))

    assert references
    assert all(
        re.search(r"@[0-9a-f]{40}$", reference)
        for reference in references
    ), references


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


def test_reusable_workflow_trust_boundary():
    workflow = load_workflow_strings("reusable-review.yml")
    assert workflow["on"]["workflow_call"]["secrets"]["api-key"]["required"] == "true"
    assert workflow["permissions"] == {}

    review = workflow["jobs"]["review"]
    assert review["permissions"] == {"contents": "read"}
    checkout = review["steps"][0]
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha }}"
    assert checkout["with"]["persist-credentials"] == "false"
    policy = review["steps"][1]
    assert policy["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert "git -C target show" in policy["run"]
    reviewer = next(step for step in review["steps"] if step.get("id") == "review")
    assert reviewer["uses"] == (
        "Zhangjinkai123/ai-code-reviewer@"
        "0e4257f42df81960a79c0b38f54bd5ce033e5da2"
    )
    assert reviewer["with"]["repo-dir"] == "target"
    cleanup = next(step for step in review["steps"] if step["name"] == "Remove previous review report")
    assert review["steps"].index(cleanup) < review["steps"].index(reviewer)
    assert cleanup["run"] == "rm -f reports/review-report.json"
    preserve = next(step for step in review["steps"] if step["name"] == "Preserve reviewer exit status")
    assert preserve["if"] == "always()"
    assert '"${REVIEW_OUTCOME}" != "success"' in preserve["run"]

    publish = workflow["jobs"]["publish"]
    assert publish["needs"] == "review"
    assert publish["permissions"]["pull-requests"] == "write"
    assert "actions" not in publish["permissions"]
    publish_checkout = publish["steps"][0]
    assert publish_checkout["with"]["repository"] == "Zhangjinkai123/ai-code-reviewer"
    assert publish_checkout["with"]["ref"] == (
        "0e4257f42df81960a79c0b38f54bd5ce033e5da2"
    )
    assert reviewer["uses"].split("@")[1] == publish_checkout["with"]["ref"]
    assert publish_checkout["with"]["persist-credentials"] == "false"
    publish_script = publish["steps"][-1]["run"]
    assert "get_pr_head_sha" in publish_script
    assert "current_sha != expected_sha" in publish_script
    assert "stale comment skipped" in publish_script
    assert not any(
        step.get("uses", "").startswith("actions/checkout@")
        and step.get("with", {}).get("repository") == "${{ github.repository }}"
        for step in publish["steps"]
    )


def test_reusable_workflow_failure_status():
    workflow = load_workflow_strings("reusable-review.yml")
    steps = workflow["jobs"]["review"]["steps"]
    script = next(
        step["run"] for step in steps
        if step["name"] == "Preserve reviewer exit status"
    )
    bash = shutil.which("bash")
    if not bash and sys.platform == "win32":
        git = shutil.which("git")
        if git:
            candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe"
            if candidate.is_file():
                bash = str(candidate)
    if not bash:
        print("Skipped shell status test: bash not found.")
        return

    for outcome, code, expected in [
        ("success", "0", 0),
        ("failure", "1", 1),
        ("failure", "2", 2),
        ("failure", "", 2),
        ("failure", "invalid", 2),
        ("skipped", "", 2),
    ]:
        env = os.environ.copy()
        env.update(REVIEW_OUTCOME=outcome, REVIEW_EXIT_CODE=code)
        completed = subprocess.run([bash, "-c", script], env=env, check=False)
        assert completed.returncode == expected, (outcome, code, completed.returncode)


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
    test_actions_are_pinned_to_full_commit_sha()
    test_reusable_workflow_trust_boundary()
    test_reusable_workflow_failure_status()
    test_dual_workflow_contract()
