import json

from reviewer.formatter import format_review_markdown
from reviewer.github import post_pr_comment
from reviewer.models import ReviewResult


def load_review_result(path: str) -> ReviewResult:
    """
    从 JSON 文件加载 ReviewResult。
    """

    with open(
        path,
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    return ReviewResult(**data)


def create_pr_comment(
    review_result_path: str,
    repo: str,
    pr_number: int,
    token: str,
) -> dict:
    """
    从 ReviewResult JSON 创建 GitHub PR Comment。
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

    # ---------------------------------------------
    # 加载 ReviewResult
    # ---------------------------------------------

    result = load_review_result(
        review_result_path
    )

    # ---------------------------------------------
    # ReviewResult -> Markdown
    # ---------------------------------------------

    markdown = format_review_markdown(
        result
    )

    # ---------------------------------------------
    # Markdown -> GitHub PR Comment
    # ---------------------------------------------

    return post_pr_comment(
        repo=repo,
        pr_number=pr_number,
        body=markdown,
        token=token,
    )