import json

from reviewer.github import (
    DEFAULT_GITHUB_API_URL,
    GitHubAPIError,
    post_pr_comment,
)


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
    assert (
        DEFAULT_GITHUB_API_URL
        == "https://api.github.com"
    )


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

    decoded = json.loads(
        encoded.decode("utf-8")
    )

    assert decoded["body"] == body


def main():
    test_invalid_repo()
    print("✓ test_invalid_repo")

    test_invalid_pr_number()
    print("✓ test_invalid_pr_number")

    test_empty_body()
    print("✓ test_empty_body")

    test_empty_token()
    print("✓ test_empty_token")

    test_default_api_url()
    print("✓ test_default_api_url")

    test_exception_class()
    print("✓ test_exception_class")

    test_json_payload()
    print("✓ test_json_payload")

    print()
    print("All GitHub API tests passed.")


if __name__ == "__main__":
    main()