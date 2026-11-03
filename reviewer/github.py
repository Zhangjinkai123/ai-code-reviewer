
import json
import urllib.error
import urllib.request


DEFAULT_GITHUB_API_URL = "https://api.github.com"
COMMENTS_PER_PAGE = 100


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
        raise ValueError("GitHub token cannot be empty")

    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

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
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body)

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
        raise ValueError("repo cannot be empty")

    if "/" not in repo:
        raise ValueError(
            "repo must use the format 'owner/repository'"
        )

    if pr_number <= 0:
        raise ValueError(
            "pr_number must be greater than 0"
        )

    if not body:
        raise ValueError("body cannot be empty")

    if not token:
        raise ValueError("GitHub token cannot be empty")

    url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{repo}"
        f"/issues/{pr_number}"
        f"/comments"
    )

    payload = {
        "body": body
    }

    return _request_json(
        method="POST",
        url=url,
        token=token,
        payload=payload,
    )

def get_pr_head_sha(
    repo: str,
    pr_number: int,
    token: str,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> str:
    """
    获取 GitHub Pull Request 最新 Head Commit SHA。
    """

    if not repo:
        raise ValueError("repo cannot be empty")

    if "/" not in repo:
        raise ValueError(
            "repo must use the format 'owner/repository'"
        )

    if pr_number <= 0:
        raise ValueError(
            "pr_number must be greater than 0"
        )

    if not token:
        raise ValueError("GitHub token cannot be empty")

    url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{repo}"
        f"/pulls/{pr_number}"
    )

    result = _request_json(
        method="GET",
        url=url,
        token=token,
    )

    if not isinstance(result, dict):
        raise GitHubAPIError(
            "GitHub API returned an unexpected PR response."
        )

    head = result.get("head")

    if not isinstance(head, dict):
        raise GitHubAPIError(
            "GitHub PR response is missing head information."
        )

    sha = head.get("sha")

    if not isinstance(sha, str) or not sha.strip():
        raise GitHubAPIError(
            "GitHub PR response is missing head commit SHA."
        )

    return sha



def list_pr_comments(
    repo: str,
    pr_number: int,
    token: str,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> list:
    """
    获取 Pull Request 的全部普通评论。

    使用 GitHub REST API 分页：
    - 每页最多 100 条
    - 从第 1 页开始
    - 最后一页不足 100 条时停止
    """

    if not repo:
        raise ValueError("repo cannot be empty")

    if "/" not in repo:
        raise ValueError(
            "repo must use the format 'owner/repository'"
        )

    if pr_number <= 0:
        raise ValueError(
            "pr_number must be greater than 0"
        )

    if not token:
        raise ValueError("GitHub token cannot be empty")

    base_url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{repo}"
        f"/issues/{pr_number}"
        f"/comments"
    )

    all_comments = []
    page = 1

    while True:
        url = (
            f"{base_url}"
            f"?per_page={COMMENTS_PER_PAGE}"
            f"&page={page}"
        )

        result = _request_json(
            method="GET",
            url=url,
            token=token,
        )

        if not isinstance(result, list):
            raise GitHubAPIError(
                "GitHub API returned an "
                "unexpected comment list."
            )

        all_comments.extend(result)

        if len(result) < COMMENTS_PER_PAGE:
            break

        page += 1

    return all_comments


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
        raise ValueError("repo cannot be empty")

    if "/" not in repo:
        raise ValueError(
            "repo must use the format 'owner/repository'"
        )

    if comment_id <= 0:
        raise ValueError(
            "comment_id must be greater than 0"
        )

    if not body:
        raise ValueError("body cannot be empty")

    if not token:
        raise ValueError("GitHub token cannot be empty")

    url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{repo}"
        f"/issues/comments/{comment_id}"
    )

    payload = {
        "body": body
    }

    return _request_json(
        method="PATCH",
        url=url,
        token=token,
        payload=payload,
    )
