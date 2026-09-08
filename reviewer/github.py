import json
import urllib.error
import urllib.request


DEFAULT_GITHUB_API_URL = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    """GitHub API 请求失败。"""

    pass


def _request_json(
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
) -> dict | list:
    """
    执行 GitHub API JSON 请求。
    """

    if not token:

        raise ValueError(
            "GitHub token cannot be empty"
        )

    data = None

    if payload is not None:

        data = json.dumps(
            payload
        ).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "ai-code-review-assistant",
        },
    )

    try:

        with urllib.request.urlopen(
            request
        ) as response:

            response_body = (
                response
                .read()
                .decode("utf-8")
            )

            return json.loads(
                response_body
            )

    except urllib.error.HTTPError as exc:

        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise GitHubAPIError(
            f"GitHub API request failed: "
            f"HTTP {exc.code} {exc.reason}\n"
            f"{error_body}"
        ) from exc

    except urllib.error.URLError as exc:

        raise GitHubAPIError(
            f"Unable to connect to GitHub API: "
            f"{exc.reason}"
        ) from exc


def post_pr_comment(
    repo: str,
    pr_number: int,
    body: str,
    token: str,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> dict:
    """
    给 GitHub Pull Request 创建一条普通评论。
    """

    if not repo:

        raise ValueError(
            "repo cannot be empty"
        )

    if "/" not in repo:

        raise ValueError(
            "repo must use the format "
            "'owner/repository'"
        )

    if pr_number <= 0:

        raise ValueError(
            "pr_number must be greater than 0"
        )

    if not body:

        raise ValueError(
            "body cannot be empty"
        )

    if not token:

        raise ValueError(
            "GitHub token cannot be empty"
        )

    url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{repo}"
        f"/issues/{pr_number}"
        f"/comments"
    )

    payload = {
        "body": body
    }

    result = _request_json(
        method="POST",
        url=url,
        token=token,
        payload=payload,
    )

    return result


def list_pr_comments(
    repo: str,
    pr_number: int,
    token: str,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> list:
    """
    获取 Pull Request 的普通评论列表。
    """

    if not repo:

        raise ValueError(
            "repo cannot be empty"
        )

    if "/" not in repo:

        raise ValueError(
            "repo must use the format "
            "'owner/repository'"
        )

    if pr_number <= 0:

        raise ValueError(
            "pr_number must be greater than 0"
        )

    if not token:

        raise ValueError(
            "GitHub token cannot be empty"
        )

    url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{repo}"
        f"/issues/{pr_number}"
        f"/comments"
    )

    result = _request_json(
        method="GET",
        url=url,
        token=token,
    )

    if not isinstance(
        result,
        list
    ):

        raise GitHubAPIError(
            "GitHub API returned an "
            "unexpected comment list."
        )

    return result


def update_pr_comment(
    repo: str,
    comment_id: int,
    body: str,
    token: str,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> dict:
    """
    更新 GitHub Pull Request 的已有普通评论。
    """

    if not repo:

        raise ValueError(
            "repo cannot be empty"
        )

    if "/" not in repo:

        raise ValueError(
            "repo must use the format "
            "'owner/repository'"
        )

    if comment_id <= 0:

        raise ValueError(
            "comment_id must be greater than 0"
        )

    if not body:

        raise ValueError(
            "body cannot be empty"
        )

    if not token:

        raise ValueError(
            "GitHub token cannot be empty"
        )

    url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{repo}"
        f"/issues/comments/{comment_id}"
    )

    payload = {
        "body": body
    }

    result = _request_json(
        method="PATCH",
        url=url,
        token=token,
        payload=payload,
    )

    return result