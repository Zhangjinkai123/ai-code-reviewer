from unittest.mock import patch

from reviewer.models import Issue, ReviewResult
from main import main


def create_test_result():
    return ReviewResult(
        issues=[
            Issue(
                file="UserService.java",
                line="24-25",
                code_snippet=(
                    '"select * from user where id="'
                    "\n"
                    "+ id;"
                ),
                severity="high",
                category="security",
                message=(
                    "id 直接拼接到 SQL 中，"
                    "可能导致 SQL Injection。"
                ),
                suggestion=(
                    "使用参数化查询，"
                    "避免直接拼接用户输入。"
                ),
            )
        ]
    )


@patch("main.post_pr_comment")
@patch("main.check_policy")
@patch("main.save_report")
@patch("main.print_report")
@patch("main.review_code")
@patch("main.get_git_diff")
def test_pr_comment_flow(
    mock_get_git_diff,
    mock_review_code,
    mock_print_report,
    mock_save_report,
    mock_check_policy,
    mock_post_pr_comment,
):

    mock_get_git_diff.return_value = (
        "fake git diff"
    )

    mock_review_code.return_value = (
        create_test_result()
    )

    mock_check_policy.return_value = True

    mock_post_pr_comment.return_value = {
        "html_url": (
            "https://github.com/"
            "owner/repository/"
            "pull/123#issuecomment-123"
        )
    }


    with patch.dict(
        "os.environ",
        {
            "GITHUB_TOKEN": "fake-token"
        }
    ):

        with patch(
            "sys.argv",
            [
                "main.py",
                "pr-comment",
                "owner/repository",
                "123"
            ]
        ):

            main()


    # ---------------------------------------------
    # 验证 Git diff 被获取
    # ---------------------------------------------

    mock_get_git_diff.assert_called_once()


    # ---------------------------------------------
    # 验证 AI Review 被执行
    # ---------------------------------------------

    mock_review_code.assert_called_once_with(
        "fake git diff"
    )


    # ---------------------------------------------
    # 验证 GitHub API 被调用
    # ---------------------------------------------

    mock_post_pr_comment.assert_called_once()


    args = mock_post_pr_comment.call_args.kwargs


    assert args["repo"] == (
        "owner/repository"
    )

    assert args["pr_number"] == 123

    assert args["token"] == (
        "fake-token"
    )


    # ---------------------------------------------
    # 验证 Markdown
    # ---------------------------------------------

    body = args["body"]

    assert "AI Code Review" in body

    assert "HIGH" in body

    assert "UserService.java" in body

    assert "24-25" in body

    assert "security" in body

    assert "SQL Injection" in body


    print(
        "✓ GitHub PR comment flow passed"
    )


if __name__ == "__main__":

    test_pr_comment_flow()

    print(
        "All PR comment tests passed."
    )