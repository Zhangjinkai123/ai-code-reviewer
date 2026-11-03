
import json
import os
import tempfile
from unittest.mock import patch

from reviewer.commenter import (
    create_pr_comment,
    filter_valid_issues,
    find_ai_review_comment,
)
from reviewer.formatter import (
    AI_REVIEW_MARKER,
)
from reviewer.models import (
    Issue,
    ReviewResult,
)


def create_test_review_file(issues=None):
    """
    创建临时 ReviewResult JSON 文件。
    """

    if issues is None:

        issues = [
            Issue(
                file="UserService.java",
                line="24-25",
                code_snippet=(
                    '"select * from user where id="'
                    "+ id;"
                ),
                severity="high",
                category="security",
                message=(
                    "id 直接拼接到 SQL 中，"
                    "可能导致 SQL Injection。"
                ),
                suggestion=(
                    "使用参数化查询。"
                ),
            )
        ]

    result = ReviewResult(
        issues=issues
    )

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    )

    json.dump(
        result.model_dump(),
        temp_file,
        ensure_ascii=False,
    )

    temp_file.close()

    return temp_file.name


def test_find_ai_review_comment_found():
    """
    测试：
    评论列表中存在 AI Review 评论。
    """

    comments = [
        {
            "id": 100,
            "body": "普通用户评论",
        },
        {
            "id": 200,
            "body": (
                f"{AI_REVIEW_MARKER}\n"
                "## 🤖 AI Code Review"
            ),
        },
    ]

    result = find_ai_review_comment(
        comments
    )

    assert result is not None
    assert result["id"] == 200

    print(
        "✓ test_find_ai_review_comment_found"
    )


def test_find_ai_review_comment_not_found():
    """
    测试：
    评论列表中不存在 AI Review 评论。
    """

    comments = [
        {
            "id": 100,
            "body": "普通用户评论",
        },
        {
            "id": 200,
            "body": "另一个普通评论",
        },
    ]

    result = find_ai_review_comment(
        comments
    )

    assert result is None

    print(
        "✓ test_find_ai_review_comment_not_found"
    )


def test_create_new_ai_comment():
    """
    测试：
    没有已有 AI Review 评论时，
    应该创建新评论。
    """

    review_file = create_test_review_file()

    try:

        with patch(
            "reviewer.commenter.list_pr_comments"
        ) as mock_list, patch(
            "reviewer.commenter.get_pr_head_sha",
            return_value="abc123456789",
        ) as mock_get_sha, patch(
            "reviewer.commenter.post_pr_comment"
        ) as mock_post, patch(
            "reviewer.commenter.update_pr_comment"
        ) as mock_update:

            mock_list.return_value = []

            mock_post.return_value = {
                "id": 123,
                "html_url": (
                    "https://github.com/test/test/"
                    "pull/1#issuecomment-123"
                ),
            }

            response = create_pr_comment(
                review_result_path=review_file,
                repo="test/test",
                pr_number=1,
                token="test-token",
            )

            mock_post.assert_called_once()
            mock_update.assert_not_called()

            assert response["id"] == 123

            print(
                "✓ test_create_new_ai_comment"
            )

    finally:

        os.unlink(
            review_file
        )


def test_update_existing_ai_comment():
    """
    测试：
    已经存在 AI Review 评论时，
    应该更新原评论。
    """

    review_file = create_test_review_file()

    try:

        with patch(
            "reviewer.commenter.list_pr_comments"
        ) as mock_list, patch(
            "reviewer.commenter.get_pr_head_sha",
            return_value="abc123456789",
        ) as mock_get_sha, patch(
            "reviewer.commenter.post_pr_comment"
        ) as mock_post, patch(
            "reviewer.commenter.update_pr_comment"
        ) as mock_update:

            mock_list.return_value = [
                {
                    "id": 456,
                    "body": (
                        f"{AI_REVIEW_MARKER}\n"
                        "旧的 AI Review 内容"
                    ),
                }
            ]

            mock_update.return_value = {
                "id": 456,
                "html_url": (
                    "https://github.com/test/test/"
                    "pull/1#issuecomment-456"
                ),
            }

            response = create_pr_comment(
                review_result_path=review_file,
                repo="test/test",
                pr_number=1,
                token="test-token",
            )

            mock_update.assert_called_once()
            mock_post.assert_not_called()

            update_kwargs = (
                mock_update.call_args.kwargs
            )

            assert (
                update_kwargs["comment_id"]
                == 456
            )

            assert (
                AI_REVIEW_MARKER
                in update_kwargs["body"]
            )

            assert response["id"] == 456

            print(
                "✓ test_update_existing_ai_comment"
            )

    finally:

        os.unlink(
            review_file
        )


def test_filter_valid_issues():
    """
    测试：
    有效问题保留，无效问题过滤。

    message 或 suggestion 为空白时，
    对应 Issue 应被过滤。
    """

    valid_issue = Issue(
        file="UserService.java",
        line="24",
        code_snippet=None,
        severity="high",
        category="security",
        message="存在 SQL 注入风险。",
        suggestion="使用参数化查询。",
    )

    invalid_message_issue = Issue(
        file="UserService.java",
        line="25",
        severity="medium",
        category="security",
        message="   ",
        suggestion="修复这个问题。",
    )

    invalid_suggestion_issue = Issue(
        file="UserService.java",
        line=None,
        severity="low",
        category="quality",
        message="存在代码质量问题。",
        suggestion="   ",
    )

    result = ReviewResult(
        issues=[
            valid_issue,
            invalid_message_issue,
            invalid_suggestion_issue,
        ]
    )

    filtered_result = filter_valid_issues(
        result
    )

    assert len(filtered_result.issues) == 1

    assert (
        filtered_result.issues[0].message
        == "存在 SQL 注入风险。"
    )

    # 原始结果不应该被修改
    assert len(result.issues) == 3

    print(
        "✓ test_filter_valid_issues"
    )


def test_all_invalid_issues_generate_no_issues_comment():
    """
    测试：
    所有 Issue 都无效时，
    应正常生成 No issues found 评论。
    """

    invalid_issues = [
        Issue(
            file="UserService.java",
            line="24",
            severity="high",
            category="security",
            message="",
            suggestion="使用参数化查询。",
        ),
        Issue(
            file="UserService.java",
            line="25",
            severity="medium",
            category="security",
            message="存在安全问题。",
            suggestion="   ",
        ),
    ]

    review_file = create_test_review_file(
        invalid_issues
    )

    try:

        with patch(
            "reviewer.commenter.list_pr_comments"
        ) as mock_list, patch(
            "reviewer.commenter.get_pr_head_sha",
            return_value="abc123456789",
        ) as mock_get_sha, patch(
            "reviewer.commenter.post_pr_comment"
        ) as mock_post:

            mock_list.return_value = []

            mock_post.return_value = {
                "id": 789,
                "html_url": (
                    "https://github.com/test/test/"
                    "pull/1#issuecomment-789"
                ),
            }

            response = create_pr_comment(
                review_result_path=review_file,
                repo="test/test",
                pr_number=1,
                token="test-token",
            )

            mock_post.assert_called_once()

            markdown = (
                mock_post.call_args.kwargs["body"]
            )

            assert (
                AI_REVIEW_MARKER
                in markdown
            )

            assert (
                "No issues found"
                in markdown
            )

            assert (
                "存在安全问题"
                not in markdown
            )

            assert response["id"] == 789

            print(
                "✓ test_all_invalid_issues_generate_no_issues_comment"
            )

    finally:

        os.unlink(
            review_file
        )

def create_issue(**kwargs):
    from reviewer.models import Issue

    data = {
        "file": "UserService.java",
        "line": "24",
        "code_snippet": None,
        "severity": "high",
        "category": "security",
        "message": "测试问题",
        "suggestion": "测试建议",
    }

    data.update(kwargs)

    return Issue(**data)

def test_filtered_issues_severity_summary():
    from reviewer.commenter import filter_valid_issues
    from reviewer.formatter import summarize_issues

    result = ReviewResult(
        issues=[
            create_issue(
                severity="high",
                message="SQL 注入风险",
                suggestion="使用参数化查询",
            ),
            create_issue(
                severity="critical",
                message="",
                suggestion="修复问题",
            ),
            create_issue(
                severity="medium",
                message="空指针风险",
                suggestion="增加空值检查",
            ),
            create_issue(
                severity="low",
                message="代码风格问题",
                suggestion="统一命名规范",
            ),
        ]
    )

    filtered_result = filter_valid_issues(result)

    summary = summarize_issues(
        filtered_result.issues
    )

    assert summary["total"] == 3
    assert summary["HIGH"] == 1
    assert summary["MEDIUM"] == 1
    assert summary["LOW"] == 1
    assert summary["CRITICAL"] == 0

    print("✓ test_filtered_issues_severity_summary")

def test_commit_sha_passed_to_formatter():
    with patch(
        "reviewer.commenter.format_review_markdown"
    ) as mock_formatter, patch(
        "reviewer.commenter.load_review_result"
    ) as mock_loader, patch(
        "reviewer.commenter.filter_valid_issues"
    ) as mock_filter, patch(
        "reviewer.commenter.list_pr_comments",
        return_value=[],
    ), patch(
        "reviewer.commenter.post_pr_comment",
        return_value={"id": 123},
    ):

        mock_loader.return_value = ReviewResult(issues=[])
        mock_filter.return_value = mock_loader.return_value
        mock_formatter.return_value = "test markdown"

        create_pr_comment(
            review_result_path="test.json",
            repo="test-owner/test-repo",
            pr_number=1,
            token="test-token",
            commit_sha="abc123456789",
        )

        mock_formatter.assert_called_once_with(
            mock_filter.return_value,
            repo="test-owner/test-repo",
            commit_sha="abc123456789",
        )

    print("✓ test_commit_sha_passed_to_formatter")

def test_commit_sha_auto_fetch():
    with patch(
        "reviewer.commenter.get_pr_head_sha",
        return_value="abc123456789",
    ) as mock_get_sha, patch(
        "reviewer.commenter.format_review_markdown"
    ) as mock_formatter, patch(
        "reviewer.commenter.load_review_result"
    ) as mock_loader, patch(
        "reviewer.commenter.filter_valid_issues"
    ) as mock_filter, patch(
        "reviewer.commenter.list_pr_comments",
        return_value=[],
    ), patch(
        "reviewer.commenter.post_pr_comment",
        return_value={"id": 123},
    ):

        mock_loader.return_value = ReviewResult(issues=[])
        mock_filter.return_value = mock_loader.return_value
        mock_formatter.return_value = "test markdown"

        create_pr_comment(
            review_result_path="test.json",
            repo="test-owner/test-repo",
            pr_number=1,
            token="test-token",
        )

        mock_get_sha.assert_called_once_with(
            repo="test-owner/test-repo",
            pr_number=1,
            token="test-token",
        )

        mock_formatter.assert_called_once_with(
            mock_filter.return_value,
            repo="test-owner/test-repo",
            commit_sha="abc123456789",
        )

    print("✓ test_commit_sha_auto_fetch")


def main():
    """
    运行所有 commenter 测试。
    """

    test_find_ai_review_comment_found()

    test_find_ai_review_comment_not_found()

    test_create_new_ai_comment()

    test_update_existing_ai_comment()

    test_filter_valid_issues()

    test_all_invalid_issues_generate_no_issues_comment()

    test_commit_sha_auto_fetch()

    print()

    print(
        "All commenter tests passed."
    )


if __name__ == "__main__":

    main()
