import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import call, patch

from git_utils.diff import get_git_diff


def test_local_diff_includes_working_tree_changes():
    with patch.dict(
        os.environ,
        {"GITHUB_BASE_SHA": ""},
    ), patch(
        "git_utils.diff.subprocess.run",
        side_effect=[
            SimpleNamespace(
                returncode=0,
                stdout="origin/master\n",
            ),
            SimpleNamespace(
                returncode=0,
                stdout="",
            ),
            SimpleNamespace(
                returncode=0,
                stdout="merge-base-sha\n",
            ),
            SimpleNamespace(
                returncode=0,
                stdout="local diff",
            ),
        ],
    ) as mock_run:
        result = get_git_diff()

    assert result == "local diff"
    assert mock_run.call_args_list[-1] == call(
        ["git", "diff", "merge-base-sha"],
        capture_output=True,
        text=True,
    )

    print("[PASS] test_local_diff_includes_working_tree_changes")


def test_actions_diff_uses_base_sha_and_head():
    with patch.dict(
        os.environ,
        {"GITHUB_BASE_SHA": "base-sha"},
    ), patch(
        "git_utils.diff.subprocess.run",
        return_value=SimpleNamespace(
            returncode=0,
            stdout="actions diff",
        ),
    ) as mock_run:
        result = get_git_diff()

    assert result == "actions diff"
    # 必须用三点 diff：两点会把 base 分支的新提交显示成反向改动。
    mock_run.assert_called_once_with(
        ["git", "diff", "base-sha...HEAD"],
        capture_output=True,
        text=True,
    )

    print("[PASS] test_actions_diff_uses_base_sha_and_head")


def test_diverged_base_excludes_base_only_changes():
    original_directory = os.getcwd()

    with tempfile.TemporaryDirectory() as directory:
        def git(*args):
            return subprocess.run(
                ["git", "-C", directory, *args],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        git("init", "-b", "base")
        git("config", "user.name", "Diff Test")
        git("config", "user.email", "diff-test@example.invalid")
        tracked = Path(directory) / "tracked.txt"
        tracked.write_text("initial\n", encoding="utf-8")
        git("add", "tracked.txt")
        git("commit", "-m", "initial")
        ancestor = git("rev-parse", "HEAD")
        base_only = Path(directory) / "base-only.txt"
        base_only.write_text("base-only\n", encoding="utf-8")
        git("add", "base-only.txt")
        git("commit", "-m", "base change")
        git("update-ref", "refs/remotes/origin/master", "HEAD")
        git("checkout", "-b", "feature", ancestor)
        tracked.write_text("feature\n", encoding="utf-8")
        git("add", "tracked.txt")
        git("commit", "-m", "feature change")
        tracked.write_text("feature\nstaged\n", encoding="utf-8")
        git("add", "tracked.txt")
        tracked.write_text("feature\nstaged\nunstaged\n", encoding="utf-8")

        try:
            os.chdir(directory)
            with patch.dict(os.environ, {"GITHUB_BASE_SHA": ""}):
                diff = get_git_diff()
        finally:
            os.chdir(original_directory)

        assert "base-only.txt" not in diff
        assert "+feature" in diff
        assert "+staged" in diff
        assert "+unstaged" in diff

    print("[PASS] test_diverged_base_excludes_base_only_changes")


def test_repo_dir_uses_git_dash_c():
    """指定 repo_dir 时所有 git 调用都必须带 -C，否则会读错仓库。"""
    with patch.dict(
        os.environ,
        {"GITHUB_BASE_SHA": ""},
    ), patch(
        "git_utils.diff.subprocess.run",
        side_effect=[
            SimpleNamespace(returncode=0, stdout="origin/master\n"),
            SimpleNamespace(returncode=0, stdout=""),
            SimpleNamespace(returncode=0, stdout="merge-base-sha\n"),
            SimpleNamespace(returncode=0, stdout="other repo diff"),
        ],
    ) as mock_run:
        result = get_git_diff(repo_dir="/path/to/other-repo")

    assert result == "other repo diff"

    for item in mock_run.call_args_list:
        command = item.args[0]
        assert command[:2] == ["git", "-C"], f"缺少 -C: {command}"
        assert command[2] == "/path/to/other-repo"

    # 关键回归：最终的 diff 命令也必须带 -C，否则会退回到进程工作目录。
    assert mock_run.call_args_list[-1] == call(
        ["git", "-C", "/path/to/other-repo", "diff", "merge-base-sha"],
        capture_output=True,
        text=True,
    )

    print("[PASS] test_repo_dir_uses_git_dash_c")


def test_base_ahead_does_not_create_reverse_diff():
    """
    base 分支在 PR 分叉后又有新提交时，不能把对方的新内容当成 PR 改动。

    这是两点 diff 的典型故障：base 上的新文件会显示成 PR 删除它，
    新增内容会显示成删除，导致虚假高危问题。
    """
    original_directory = os.getcwd()

    with tempfile.TemporaryDirectory() as directory:
        def git(*args):
            return subprocess.run(
                ["git", "-C", directory, *args],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        git("init", "-b", "master")
        git("config", "user.name", "Diff Test")
        git("config", "user.email", "diff-test@example.invalid")

        app = Path(directory) / "app.py"
        app.write_text("a\n", encoding="utf-8")
        git("add", "app.py")
        git("commit", "-m", "base")

        # PR 分支：只追加一行
        git("checkout", "-b", "feature")
        app.write_text("a\nPR-CHANGE\n", encoding="utf-8")
        git("add", "app.py")
        git("commit", "-m", "pr change")

        # base 分支继续前进：改动同一文件，并新增一个文件
        git("checkout", "master")
        app.write_text("a\nMASTER-ONLY\n", encoding="utf-8")
        (Path(directory) / "unrelated.md").write_text(
            "someone else\n", encoding="utf-8"
        )
        git("add", "app.py", "unrelated.md")
        git("commit", "-m", "master moved on")

        base_sha = git("rev-parse", "master")

        git("checkout", "feature")

        try:
            os.chdir(directory)
            with patch.dict(os.environ, {"GITHUB_BASE_SHA": base_sha}):
                diff = get_git_diff()
        finally:
            os.chdir(original_directory)

        # 只应包含 PR 自己新增的那一行
        assert "+PR-CHANGE" in diff

        # 不得出现反向改动或 base 上的无关文件
        assert "MASTER-ONLY" not in diff
        assert "unrelated.md" not in diff

    print("[PASS] test_base_ahead_does_not_create_reverse_diff")


def main():
    test_local_diff_includes_working_tree_changes()
    test_actions_diff_uses_base_sha_and_head()
    test_diverged_base_excludes_base_only_changes()
    test_repo_dir_uses_git_dash_c()
    test_base_ahead_does_not_create_reverse_diff()
    print()
    print("All Git diff tests passed.")


if __name__ == "__main__":
    main()
