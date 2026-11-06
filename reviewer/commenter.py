import json

from reviewer.formatter import format_review_markdown
from reviewer.github import post_pr_comment
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

    return ReviewResult.model_validate(
        data
    )


def filter_valid_issues(
    result: ReviewResult,
) -> ReviewResult:
    """
    过滤无效的 Review Issue。

    过滤规则：
    1. message 必须是非空字符串。
    2. suggestion 必须是非空字符串。
    3. 其他字段不参与有效性判断。
    """

    valid_issues = []

    for issue in result.issues or []:
        message = issue.message
        suggestion = issue.suggestion

        if not isinstance(message, str):
            continue

        if not isinstance(suggestion, str):
            continue

        if not message.strip():
            continue

        if not suggestion.strip():
            continue

        valid_issues.append(issue)

    return ReviewResult(
        issues=valid_issues
    )


def create_pr_comment(
    review_result_path: str,
    repo: str,
    pr_number: int,
    token: str,
    commit_sha: str,
) -> dict:
    """
    为 GitHub PR 创建一条独立的 AI Review Comment。

    每次 Commit 审查都创建新评论，
    不查询、不去重、不更新历史评论。
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

    if not commit_sha:
        raise ValueError(
            "commit_sha cannot be empty"
        )

    # -------------------------------------------------
    # 1. 加载 ReviewResult
    # -------------------------------------------------

    result = load_review_result(
        review_result_path
    )

    # -------------------------------------------------
    # 2. 过滤无效 Review Issue
    # -------------------------------------------------

    result = filter_valid_issues(
        result
    )

    # -------------------------------------------------
    # 3. ReviewResult -> Markdown
    # -------------------------------------------------

    markdown = format_review_markdown(
        result,
        repo=repo,
        commit_sha=commit_sha,
    )

    # -------------------------------------------------
    # 4. 每次审查直接创建一条新评论
    # -------------------------------------------------

    return post_pr_comment(
        repo=repo,
        pr_number=pr_number,
        body=markdown,
        token=token,
    )
