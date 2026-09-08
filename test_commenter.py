import json
import tempfile
from unittest.mock import patch

from reviewer.commenter import (
    create_pr_comment,
    find_ai_review_comment,
)
from reviewer.formatter import (
    AI_REVIEW_MARKER,
)
from reviewer.models import (
    Issue,
    ReviewResult,
)


def create_test_review_file():
    """
    创建临时 ReviewResult JSON 文件。
    """

    result = ReviewResult(
        issues=[
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

            # 应该调用创建
            mock_post.assert_called_once()

            # 不应该调用更新
            mock_update.assert_not_called()

            assert response["id"] == 123

            print(
                "✓ test_create_new_ai_comment"
            )

    finally:

        import os

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

            # 应该调用更新
            mock_update.assert_called_once()

            # 不应该创建新评论
            mock_post.assert_not_called()

            # 检查使用的是正确的 comment_id
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

        import os

        os.unlink(
            review_file
        )


def main():
    """
    运行所有 commenter 测试。
    """

    test_find_ai_review_comment_found()

    test_find_ai_review_comment_not_found()

    test_create_new_ai_comment()

    test_update_existing_ai_comment()

    print()

    print(
        "All commenter tests passed."
    )


if __name__ == "__main__":

    main()