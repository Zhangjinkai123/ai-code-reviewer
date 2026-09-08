import json

from reviewer.formatter import (
    AI_REVIEW_MARKER,
    format_review_markdown,
)
from reviewer.github import (
    list_pr_comments,
    post_pr_comment,
    update_pr_comment,
)
from reviewer.models import ReviewResult


def load_review_result(
    path: str,
) -> ReviewResult:
    """
    从 JSON 文件加载 ReviewResult。
    """

    with open(
        path,
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    return ReviewResult(
        **data
    )


def find_ai_review_comment(
    comments: list,
) -> dict | None:
    """
    在 PR 评论列表中寻找 AI Reviewer 创建的评论。

    通过 AI_REVIEW_MARKER 判断评论是否属于
    AI Code Review Assistant。
    """

    for comment in comments:

        body = comment.get(
            "body",
            "",
        )

        if AI_REVIEW_MARKER in body:

            return comment

    return None


def create_pr_comment(
    review_result_path: str,
    repo: str,
    pr_number: int,
    token: str,
) -> dict:
    """
    创建或更新 GitHub PR 的 AI Review Comment。

    如果 PR 中已经存在 AI Review 评论，
    则更新已有评论。

    如果不存在，
    则创建新评论。
    """

    if not review_result_path:

        raise ValueError(
            "review_result_path cannot be empty"
        )

    if not repo:

        raise ValueError(
            "repo cannot be empty"
        )

    if pr_number <= 0:

        raise ValueError(
            "pr_number must be greater than 0"
        )

    if not token:

        raise ValueError(
            "GitHub token cannot be empty"
        )

    # -------------------------------------------------
    # 1. 加载 ReviewResult
    # -------------------------------------------------

    result = load_review_result(
        review_result_path
    )

    # -------------------------------------------------
    # 2. ReviewResult -> Markdown
    # -------------------------------------------------

    markdown = format_review_markdown(
        result
    )

    # -------------------------------------------------
    # 3. 获取 PR 现有评论
    # -------------------------------------------------

    comments = list_pr_comments(
        repo=repo,
        pr_number=pr_number,
        token=token,
    )

    # -------------------------------------------------
    # 4. 查找已有 AI Review 评论
    # -------------------------------------------------

    existing_comment = find_ai_review_comment(
        comments
    )

    # -------------------------------------------------
    # 5. 已存在 -> 更新
    # -------------------------------------------------

    if existing_comment:

        comment_id = existing_comment.get(
            "id"
        )

        if not comment_id:

            raise RuntimeError(
                "AI Review comment was found "
                "but its comment ID is missing."
            )

        return update_pr_comment(
            repo=repo,
            comment_id=comment_id,
            body=markdown,
            token=token,
        )

    # -------------------------------------------------
    # 6. 不存在 -> 创建
    # -------------------------------------------------

    return post_pr_comment(
        repo=repo,
        pr_number=pr_number,
        body=markdown,
        token=token,
    )