
import io
import json
import urllib.error
from unittest.mock import MagicMock, call, patch

from reviewer.github import (
    COMMENTS_PER_PAGE,
    DEFAULT_GITHUB_API_URL,
    GitHubAPIError,
    list_pr_comments,
    post_pr_comment,
    update_pr_comment,
    get_pr_head_sha,
)


def make_response(data):
    """构造模拟的 HTTP 响应。"""

    response = MagicMock()
    response.read.return_value = json.dumps(
        data
    ).encode("utf-8")

    return response


def test_invalid_repo():
    try:
        post_pr_comment(
            repo="invalid-repo",
            pr_number=1,
            body="test",
            token="fake-token",
        )
    except ValueError as exc:
        assert "owner/repository" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for invalid repo"
        )


def test_invalid_pr_number():
    try:
        post_pr_comment(
            repo="owner/repository",
            pr_number=0,
            body="test",
            token="fake-token",
        )
    except ValueError as exc:
        assert "pr_number" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for invalid PR number"
        )


def test_empty_body():
    try:
        post_pr_comment(
            repo="owner/repository",
            pr_number=1,
            body="",
            token="fake-token",
        )
    except ValueError as exc:
        assert "body" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for empty body"
        )


def test_empty_token():
    try:
        post_pr_comment(
            repo="owner/repository",
            pr_number=1,
            body="test",
            token="",
        )
    except ValueError as exc:
        assert "token" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for empty token"
        )


def test_default_api_url():
    assert DEFAULT_GITHUB_API_URL == "https://api.github.com"


def test_exception_class():
    error = GitHubAPIError("test error")

    assert isinstance(error, RuntimeError)
    assert str(error) == "test error"


def test_json_payload():
    body = "## 🤖 AI Code Review\n\nFound 1 issue."

    payload = {
        "body": body
    }

    encoded = json.dumps(payload).encode("utf-8")
    decoded = json.loads(encoded.decode("utf-8"))

    assert decoded["body"] == body


def test_post_pr_comment_http_request():
    body = "AI review result"

    with patch(
        "reviewer.github.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = (
            make_response({"id": 123})
        )

        result = post_pr_comment(
            repo="owner/repository",
            pr_number=10,
            body=body,
            token="fake-token",
            api_url="https://api.github.com",
        )

    assert result["id"] == 123
    mock_urlopen.assert_called_once()

    request = mock_urlopen.call_args.args[0]

    assert request.get_method() == "POST"
    assert request.full_url == (
        "https://api.github.com/repos/owner/repository"
        "/issues/10/comments"
    )
    assert request.get_header("Authorization") == "Bearer fake-token"
    assert request.get_header("Accept") == "application/vnd.github+json"

    payload = json.loads(request.data.decode("utf-8"))
    assert payload["body"] == body


def test_list_pr_comments_http_request():
    comments = [
        {"id": 1, "body": "comment 1"},
        {"id": 2, "body": "comment 2"},
    ]

    with patch(
        "reviewer.github.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = (
            make_response(comments)
        )

        result = list_pr_comments(
            repo="owner/repository",
            pr_number=10,
            token="fake-token",
        )

    assert result == comments
    mock_urlopen.assert_called_once()

    request = mock_urlopen.call_args.args[0]

    assert request.get_method() == "GET"
    assert request.full_url == (
        "https://api.github.com/repos/owner/repository"
        "/issues/10/comments?per_page=100&page=1"
    )


def test_list_pr_comments_pagination():
    first_page = [
        {"id": i, "body": f"comment {i}"}
        for i in range(1, COMMENTS_PER_PAGE + 1)
    ]

    second_page = [
        {"id": 101, "body": "comment 101"},
        {"id": 102, "body": "comment 102"},
    ]

    with patch(
        "reviewer.github.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_urlopen.side_effect = [
            MagicMock(
                __enter__=MagicMock(
                    return_value=make_response(first_page)
                )
            ),
            MagicMock(
                __enter__=MagicMock(
                    return_value=make_response(second_page)
                )
            ),
        ]

        result = list_pr_comments(
            repo="owner/repository",
            pr_number=10,
            token="fake-token",
        )

    assert len(result) == 102
    assert result[0]["id"] == 1
    assert result[-1]["id"] == 102
    assert mock_urlopen.call_count == 2

    first_request = mock_urlopen.call_args_list[0].args[0]
    second_request = mock_urlopen.call_args_list[1].args[0]

    assert first_request.full_url.endswith(
        "?per_page=100&page=1"
    )
    assert second_request.full_url.endswith(
        "?per_page=100&page=2"
    )


def test_list_pr_comments_rejects_invalid_response():
    with patch(
        "reviewer.github.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = (
            make_response({"message": "unexpected"})
        )

        try:
            list_pr_comments(
                repo="owner/repository",
                pr_number=10,
                token="fake-token",
            )
        except GitHubAPIError as exc:
            assert "unexpected comment list" in str(exc)
        else:
            raise AssertionError(
                "Expected GitHubAPIError for invalid response"
            )


def test_update_pr_comment_http_request():
    body = "Updated AI review result"

    with patch(
        "reviewer.github.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = (
            make_response({"id": 456, "body": body})
        )

        result = update_pr_comment(
            repo="owner/repository",
            comment_id=456,
            body=body,
            token="fake-token",
        )

    assert result["id"] == 456
    mock_urlopen.assert_called_once()

    request = mock_urlopen.call_args.args[0]

    assert request.get_method() == "PATCH"
    assert request.full_url == (
        "https://api.github.com/repos/owner/repository"
        "/issues/comments/456"
    )

    payload = json.loads(request.data.decode("utf-8"))
    assert payload["body"] == body


def test_http_error():
    error = urllib.error.HTTPError(
        url="https://api.github.com/test",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=io.BytesIO(b'{"message":"Forbidden"}'),
    )

    with patch(
        "reviewer.github.urllib.request.urlopen",
        side_effect=error,
    ):
        try:
            post_pr_comment(
                repo="owner/repository",
                pr_number=10,
                body="test",
                token="fake-token",
            )
        except GitHubAPIError as exc:
            assert "HTTP 403" in str(exc)
            assert "Forbidden" in str(exc)
        else:
            raise AssertionError(
                "Expected GitHubAPIError for HTTP error"
            )


def test_url_error():
    error = urllib.error.URLError("Connection refused")

    with patch(
        "reviewer.github.urllib.request.urlopen",
        side_effect=error,
    ):
        try:
            post_pr_comment(
                repo="owner/repository",
                pr_number=10,
                body="test",
                token="fake-token",
            )
        except GitHubAPIError as exc:
            assert "Unable to connect" in str(exc)
        else:
            raise AssertionError(
                "Expected GitHubAPIError for URL error"
            )

        
def test_get_pr_head_sha():
    expected_sha = "abc123456789"

    with patch(
        "reviewer.github._request_json"
    ) as mock_request:

        mock_request.return_value = {
            "head": {
                "sha": expected_sha
            }
        }

        sha = get_pr_head_sha(
            repo="owner/repository",
            pr_number=123,
            token="fake-token",
        )

        assert sha == expected_sha

        mock_request.assert_called_once_with(
            method="GET",
            url=(
                "https://api.github.com"
                "/repos/owner/repository/pulls/123"
            ),
            token="fake-token",
        )

    print("✓ test_get_pr_head_sha")


def test_get_pr_head_sha_invalid_response():
    with patch(
        "reviewer.github._request_json"
    ) as mock_request:

        mock_request.return_value = {}

        try:
            get_pr_head_sha(
                repo="owner/repository",
                pr_number=123,
                token="fake-token",
            )
        except GitHubAPIError:
            pass
        else:
            raise AssertionError(
                "Expected GitHubAPIError"
            )

    print("✓ test_get_pr_head_sha_invalid_response")



def main():
    tests = [
        test_invalid_repo,
        test_invalid_pr_number,
        test_empty_body,
        test_empty_token,
        test_default_api_url,
        test_exception_class,
        test_json_payload,
        test_post_pr_comment_http_request,
        test_list_pr_comments_http_request,
        test_list_pr_comments_pagination,
        test_list_pr_comments_rejects_invalid_response,
        test_update_pr_comment_http_request,
        test_http_error,
        test_url_error,
        test_get_pr_head_sha,
        test_get_pr_head_sha_invalid_response,

    ]

    for test in tests:
        test()
        print(f"✓ {test.__name__}")

    print()
    print("All GitHub API tests passed.")


if __name__ == "__main__":
    main()
