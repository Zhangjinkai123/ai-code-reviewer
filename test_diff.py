import os
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
                stdout="local diff",
            ),
        ],
    ) as mock_run:
        result = get_git_diff()

    assert result == "local diff"
    assert mock_run.call_args_list[-1] == call(
        ["git", "diff", "origin/master"],
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
    mock_run.assert_called_once_with(
        ["git", "diff", "base-sha", "HEAD"],
        capture_output=True,
        text=True,
    )

    print("[PASS] test_actions_diff_uses_base_sha_and_head")


def main():
    test_local_diff_includes_working_tree_changes()
    test_actions_diff_uses_base_sha_and_head()
    print()
    print("All Git diff tests passed.")


if __name__ == "__main__":
    main()
