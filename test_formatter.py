
from reviewer.models import Issue, ReviewResult

from reviewer.formatter import (
    AI_REVIEW_MARKER,
    escape_markdown,
    format_code_block,
    format_inline_code,
    format_review_markdown,
)


def create_issue(**kwargs):
    data = {
        "file": "UserService.java",
        "line": "24-25",
        "code_snippet": 'String sql = "select * from user";',
        "severity": "high",
        "category": "security",
        "message": "存在 SQL Injection 风险。",
        "suggestion": "使用参数化查询。",
    }

    data.update(kwargs)

    return Issue(**data)


def test_basic_markdown():
    result = ReviewResult(
        issues=[create_issue()]
    )

    markdown = format_review_markdown(result)

    assert AI_REVIEW_MARKER in markdown
    assert "AI Code Review" in markdown
    assert "HIGH" in markdown
    assert "UserService.java" in markdown
    assert "24-25" in markdown
    assert "SQL Injection" in markdown

    print("[PASS] test_basic_markdown")


def test_empty_result():
    result = ReviewResult(
        issues=[]
    )

    markdown = format_review_markdown(result)

    assert "No issues found" in markdown
    assert AI_REVIEW_MARKER in markdown

    print("[PASS] test_empty_result")


def test_markdown_special_characters():
    text = "SQL *Injection* [danger] <script>"

    escaped = escape_markdown(text)

    assert r"\*" in escaped
    assert r"\[" in escaped
    assert r"\<" in escaped
    assert r"\>" in escaped

    print("[PASS] test_markdown_special_characters")


def test_inline_code_backticks():
    value = "file`name``.java"

    formatted = format_inline_code(value)

    assert formatted.startswith("```")
    assert formatted.endswith("```")

    print("[PASS] test_inline_code_backticks")


def test_code_block_backticks():
    code = 'String value = "```";'

    formatted = format_code_block(code)

    assert formatted.startswith("````java")
    assert formatted.endswith("````")

    print("[PASS] test_code_block_backticks")


def test_special_characters_in_issue():
    result = ReviewResult(
        issues=[
            create_issue(
                file="src/[test]*.java",
                message="发现 *严重* 问题，涉及 [SQL] 注入。",
                suggestion="使用 `PreparedStatement`。",
                code_snippet='String sql = "```";',
            )
        ]
    )

    markdown = format_review_markdown(result)

    assert r"\[" in markdown
    assert r"\*" in markdown
    assert r"\`" in markdown
    assert "````java" in markdown

    print("[PASS] test_special_characters_in_issue")


def test_missing_optional_fields():
    result = ReviewResult(
        issues=[
            create_issue(
                line=None,
                code_snippet=None,
                file="",
                category="",
            )
        ]
    )

    markdown = format_review_markdown(result)

    assert "unknown" in markdown
    assert "Line:" not in markdown
    assert "未分类" in markdown
    assert "未提供" not in markdown

    print("[PASS] test_missing_optional_fields")

def test_comment_length_limit():
    from reviewer.formatter import MAX_COMMENT_LENGTH

    result = ReviewResult(
        issues=[
            create_issue(
                message="问题描述。" * 10000,
                suggestion="修改建议。" * 10000,
            )
        ]
    )

    markdown = format_review_markdown(result)

    assert len(markdown) <= MAX_COMMENT_LENGTH
    assert AI_REVIEW_MARKER in markdown
    assert "评论内容过长" in markdown

    print("[PASS] test_comment_length_limit")


def test_comment_without_truncation():
    result = ReviewResult(
        issues=[create_issue()]
    )

    markdown = format_review_markdown(result)

    assert "评论内容过长" not in markdown
    assert AI_REVIEW_MARKER in markdown

    print("[PASS] test_comment_without_truncation")

def test_single_issue_formatting_isolation():
    from unittest.mock import patch
    from reviewer.formatter import _format_issue

    result = ReviewResult(
        issues=[
            create_issue(),
            create_issue(
                message="另一个正常的问题",
                suggestion="正常修改建议",
            ),
        ]
    )

    original_format_issue = _format_issue

    def mock_format_issue(
    issue,
    index,
    repo=None,
    commit_sha=None,
    ):
        if index == 1:
            raise RuntimeError("模拟格式化异常")

        return original_format_issue(
            issue,
            index,
            repo=repo,
            commit_sha=commit_sha,
        )

    with patch(
        "reviewer.formatter._format_issue",
        side_effect=mock_format_issue,
    ):
        markdown = format_review_markdown(result)

    assert AI_REVIEW_MARKER in markdown
    assert "另一个正常的问题" in markdown
    assert "SQL Injection" not in markdown

    print("[PASS] test_single_issue_formatting_isolation")

def test_severity_summary():
    from reviewer.formatter import summarize_issues

    issues = [
        create_issue(severity="critical"),
        create_issue(severity="high"),
        create_issue(severity="high"),
        create_issue(severity="medium"),
        create_issue(severity="low"),
        create_issue(severity="unknown"),
    ]

    summary = summarize_issues(issues)

    assert summary["total"] == 6
    assert summary["CRITICAL"] == 1
    assert summary["HIGH"] == 2
    assert summary["MEDIUM"] == 1
    assert summary["LOW"] == 1
    assert summary["UNKNOWN"] == 1

    print("[PASS] test_severity_summary")

def test_severity_summary_case_insensitive():
    from reviewer.formatter import summarize_issues

    issues = [
        create_issue(severity="HIGH"),
        create_issue(severity="high"),
        create_issue(severity="High"),
        create_issue(severity="medium"),
    ]

    summary = summarize_issues(issues)

    assert summary["total"] == 4
    assert summary["HIGH"] == 3
    assert summary["MEDIUM"] == 1

    print("[PASS] test_severity_summary_case_insensitive")


def test_severity_summary_unknown():
    from reviewer.formatter import summarize_issues

    issues = [
        create_issue(severity="blocker"),
        create_issue(severity="info"),
        create_issue(severity=""),
    ]

    summary = summarize_issues(issues)

    assert summary["total"] == 3
    assert summary["UNKNOWN"] == 3

    print("[PASS] test_severity_summary_unknown")


def test_severity_summary_empty():
    from reviewer.formatter import summarize_issues

    summary = summarize_issues([])

    assert summary["total"] == 0
    assert summary["CRITICAL"] == 0
    assert summary["HIGH"] == 0
    assert summary["MEDIUM"] == 0
    assert summary["LOW"] == 0
    assert summary["UNKNOWN"] == 0

    print("[PASS] test_severity_summary_empty")

def test_severity_summary_in_markdown():
    result = ReviewResult(
        issues=[
            create_issue(severity="critical"),
            create_issue(severity="high"),
            create_issue(severity="high"),
            create_issue(severity="medium"),
            create_issue(severity="low"),
        ]
    )

    markdown = format_review_markdown(result)

    assert "Found **5 issue(s)**." in markdown
    assert "| CRITICAL | 1 |" in markdown
    assert "| HIGH | 2 |" in markdown
    assert "| MEDIUM | 1 |" in markdown
    assert "| LOW | 1 |" in markdown
    assert "| UNKNOWN | 0 |" in markdown

    print("[PASS] test_severity_summary_in_markdown")

def test_github_file_link():
    result = ReviewResult(
        issues=[
            create_issue(
                file="src/UserService.java",
                line="24-25",
            )
        ]
    )

    markdown = format_review_markdown(
        result,
        repo="test-owner/test-repo",
        commit_sha="abc123456789",
    )

    assert (
        "https://github.com/test-owner/test-repo/blob/"
        "abc123456789/src/UserService.java"
    ) in markdown

    assert "[`src/UserService.java`](https://github.com/" in markdown

    print("[PASS] test_github_file_link")


def test_without_github_context():
    result = ReviewResult(
        issues=[create_issue()]
    )

    markdown = format_review_markdown(result)

    assert "https://github.com/" not in markdown
    assert "**File:** `UserService.java`" in markdown

    print("[PASS] test_without_github_context")

def test_github_line_link():
    result = ReviewResult(
        issues=[
            create_issue(
                file="src/UserService.java",
                line="24-25",
            )
        ]
    )

    markdown = format_review_markdown(
        result,
        repo="test-owner/test-repo",
        commit_sha="abc123456789",
    )

    assert "#L24-L25" in markdown

    print("[PASS] test_github_line_link")


def test_github_single_line_link():
    result = ReviewResult(
        issues=[
            create_issue(
                file="src/UserService.java",
                line="24",
            )
        ]
    )

    markdown = format_review_markdown(
        result,
        repo="test-owner/test-repo",
        commit_sha="abc123456789",
    )

    assert "#L24" in markdown

    print("[PASS] test_github_single_line_link")





def main():
    test_basic_markdown()
    test_empty_result()
    test_markdown_special_characters()
    test_inline_code_backticks()
    test_code_block_backticks()
    test_special_characters_in_issue()
    test_missing_optional_fields()
    test_comment_length_limit()
    test_comment_without_truncation()
    test_single_issue_formatting_isolation()
    test_severity_summary()
    test_severity_summary_case_insensitive()
    test_severity_summary_unknown()
    test_severity_summary_empty()
    test_severity_summary_in_markdown()
    test_github_file_link()
    test_without_github_context()
    test_github_line_link()
    test_github_single_line_link()


    print()
    print("All formatter tests passed.")


if __name__ == "__main__":
    main()
