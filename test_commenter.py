import json
import os
import tempfile
from unittest.mock import patch

from reviewer.commenter import (
    create_pr_comment,
    filter_valid_issues,
)
from reviewer.formatter import AI_REVIEW_MARKER
from reviewer.models import (
    Issue,
    ReviewResult,
)


def create_test_review_file(issues=None):

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
                suggestion="使用参数化查询。",
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


def test_create_independent_comment():

    review_file = create_test_review_file()

    try:

        with patch(
            "reviewer.commenter.post_pr_comment"
        ) as mock_post:

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
                commit_sha="abc123456789",
            )

            mock_post.assert_called_once()

            call_kwargs = mock_post.call_args.kwargs

            assert call_kwargs["repo"] == "test/test"
            assert call_kwargs["pr_number"] == 1
            assert call_kwargs["token"] == "test-token"
            assert AI_REVIEW_MARKER in call_kwargs["body"]
            assert "abc123456789" in call_kwargs["body"]
            assert response["id"] == 123

            print("[PASS] test_create_independent_comment")

    finally:

        os.unlink(review_file)


def test_commit_sha_required():

    review_file = create_test_review_file()

    try:

        try:
            create_pr_comment(
                review_result_path=review_file,
                repo="test/test",
                pr_number=1,
                token="test-token",
                commit_sha="",
            )
        except ValueError as exc:
            assert "commit_sha" in str(exc)
        else:
            raise AssertionError(
                "Expected ValueError for empty commit SHA"
            )

        print("[PASS] test_commit_sha_required")

    finally:

        os.unlink(review_file)


def test_filter_valid_issues():

    valid_issue = Issue(
        file="UserService.java",
        line="24",
        category="security",
        severity="high",
        message="存在 SQL 注入风险。",
        suggestion="使用参数化查询。",
    )

    invalid_message_issue = Issue(
        file="UserService.java",
        line="25",
        category="security",
        severity="medium",
        message="   ",
        suggestion="修复这个问题。",
    )

    invalid_suggestion_issue = Issue(
        file="UserService.java",
        line=None,
        category="quality",
        severity="low",
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

    filtered_result = filter_valid_issues(result)

    assert len(filtered_result.issues) == 1
    assert filtered_result.issues[0].message == (
        "存在 SQL 注入风险。"
    )
    assert len(result.issues) == 3

    print("[PASS] test_filter_valid_issues")


def test_all_invalid_issues_generate_no_issues_comment():

    invalid_issues = [
        Issue(
            file="UserService.java",
            line="24",
            category="security",
            severity="high",
            message="",
            suggestion="使用参数化查询。",
        ),
        Issue(
            file="UserService.java",
            line="25",
            category="security",
            severity="medium",
            message="存在安全问题。",
            suggestion="   ",
        ),
    ]

    review_file = create_test_review_file(invalid_issues)

    try:

        with patch(
            "reviewer.commenter.post_pr_comment"
        ) as mock_post:

            mock_post.return_value = {
                "id": 789,
            }

            response = create_pr_comment(
                review_result_path=review_file,
                repo="test/test",
                pr_number=1,
                token="test-token",
                commit_sha="abc123456789",
            )

            mock_post.assert_called_once()

            markdown = mock_post.call_args.kwargs["body"]

            assert AI_REVIEW_MARKER in markdown
            assert "No issues found" in markdown
            assert "存在安全问题" not in markdown
            assert response["id"] == 789

            print(
                "[PASS] test_all_invalid_issues_generate_no_issues_comment"
            )

    finally:

        os.unlink(review_file)


def main():

    test_create_independent_comment()
    test_commit_sha_required()
    test_filter_valid_issues()
    test_all_invalid_issues_generate_no_issues_comment()

    print()
    print("All commenter tests passed.")


if __name__ == "__main__":
    main()
