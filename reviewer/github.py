import json
import urllib.error
import urllib.request


DEFAULT_GITHUB_API_URL = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    """GitHub API 请求失败。"""

    pass


def post_pr_comment(
    repo: str,
    pr_number: int,
    body: str,
    token: str,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> dict:
    """
    给 GitHub Pull Request 创建一条普通评论。

    参数：
        repo:
            GitHub 仓库，格式：
            owner/repository

        pr_number:
            Pull Request 编号

        body:
            评论内容，Markdown 格式

        token:
            GitHub Personal Access Token / Actions Token

        api_url:
            GitHub API 地址。
            默认：https://api.github.com

    返回：
        GitHub API 返回的 JSON 数据。
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

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
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
            f"Unable to connect to GitHub API: {exc.reason}"
        ) from exc