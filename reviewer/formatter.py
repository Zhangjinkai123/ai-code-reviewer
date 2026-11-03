
from reviewer.models import ReviewResult


AI_REVIEW_MARKER = "<!-- ai-code-review-assistant -->"
MAX_COMMENT_LENGTH = 60000
TRUNCATION_NOTICE = "\n\n> ⚠️ 评论内容过长，部分 Review 内容已省略。"
SEVERITY_LEVELS = [
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
]

def escape_markdown(text: str) -> str:
    """
    转义普通文本中的 Markdown 特殊字符。
    """
    special_chars = r"\`*_{}[]<>()#+-.!|"

    result = str(text)

    for char in special_chars:
        result = result.replace(
            char,
            "\\" + char
        )

    return result


def format_inline_code(text: str) -> str:
    """
    安全地将文本包装为 Markdown 行内代码。
    根据内容中的反引号数量动态选择分隔符。
    """
    text = str(text)

    max_backticks = 0
    current = 0

    for char in text:
        if char == "`":
            current += 1
            max_backticks = max(
                max_backticks,
                current
            )
        else:
            current = 0

    delimiter = "`" * (max_backticks + 1)

    if text.startswith("`") or text.endswith("`"):
        text = f" {text} "

    return f"{delimiter}{text}{delimiter}"


def format_code_block(code: str) -> str:
    """
    安全地生成 Java 代码块。
    自动选择比代码内容中最长连续反引号更长的围栏。
    """
    code = str(code)

    max_backticks = 0
    current = 0

    for char in code:
        if char == "`":
            current += 1
            max_backticks = max(
                max_backticks,
                current
            )
        else:
            current = 0

    fence = "`" * max(3, max_backticks + 1)

    return "\n".join([
        f"{fence}java",
        code,
        fence,
    ])


def _get_text(value, default: str = "") -> str:
    """
    安全获取字段文本。
    兼容 None 和空字符串。
    """
    if value is None:
        return default

    text = str(value).strip()

    return text if text else default
def summarize_issues(issues: list) -> dict:
    """
    统计 Review Issue 的数量和严重程度分布。
    """

    summary = {
        "total": len(issues),
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "UNKNOWN": 0,
    }

    for issue in issues:
        severity = _get_text(
            issue.severity,
            "UNKNOWN"
        ).upper()

        if severity not in SEVERITY_LEVELS:
            severity = "UNKNOWN"

        summary[severity] += 1

    return summary


def _format_issue(
    issue,
    index: int,
    repo: str | None = None,
    commit_sha: str | None = None,
) -> str:
    """
    格式化单个 Issue。
    单个 Issue 格式化失败时，由调用方隔离异常。
    """

    severity = _get_text(
        issue.severity,
        "UNKNOWN"
    ).upper()

    file = _get_text(
        issue.file,
        "unknown"
    )

    line = _get_text(
        issue.line
    )

    category = _get_text(
        issue.category,
        "未分类"
    )

    message = _get_text(
        issue.message,
        "未提供问题描述"
    )

    suggestion = _get_text(
        issue.suggestion,
        "未提供修改建议"
    )

    code_snippet = _get_text(
        issue.code_snippet
    )

    file_display = format_inline_code(file)

    if repo and commit_sha:
        from urllib.parse import quote

        file_path = quote(file, safe="/")
        file_url = (
            f"https://github.com/{repo}/blob/"
            f"{commit_sha}/{file_path}"
        )

        if line:
            import re

            match = re.fullmatch(r"(\d+)(?:-(\d+))?", str(line))

            if match:
                start_line = match.group(1)
                end_line = match.group(2)

                if end_line:
                    file_url += f"#L{start_line}-L{end_line}"
                else:
                    file_url += f"#L{start_line}"

        file_display = f"[{file_display}]({file_url})"

    lines = [
        f"### {index}. {escape_markdown(severity)}",
        "",
        f"**File:** {file_display}",
    ]

    if line:
        lines.append(
            f"**Line:** {format_inline_code(line)}"
        )

    lines.extend([
        f"**Category:** {format_inline_code(category)}",
        "",
        "**Problem**",
        "",
        escape_markdown(message),
        "",
        "**Suggestion**",
        "",
        escape_markdown(suggestion),
        "",
    ])

    if code_snippet:
        lines.extend([
            "**Code**",
            "",
            format_code_block(code_snippet),
            "",
        ])

    lines.extend([
        "---",
        "",
    ])

    return "\n".join(lines)


def _truncate_comment(
    markdown: str,
    max_length: int = MAX_COMMENT_LENGTH,
) -> str:
    """
    限制评论长度，保留 AI Review 标记和截断提示。
    """

    if len(markdown) <= max_length:
        return markdown

    notice = TRUNCATION_NOTICE

    available_length = max_length - len(notice)

    if available_length <= 0:
        return markdown[:max_length]

    return markdown[:available_length].rstrip() + notice


def format_review_markdown(
    result: ReviewResult,
    repo: str | None = None,
    commit_sha: str | None = None,
) -> str:
    """
    将 ReviewResult 转换成 GitHub PR Comment 使用的 Markdown。

    特性：
    1. 保留评论标记。
    2. 隔离单个 Issue 的格式化异常。
    3. 限制最终评论长度。
    """

    lines = [
        AI_REVIEW_MARKER,
        "",
        "## 🤖 AI Code Review",
        "",
    ]

    issues = result.issues or []

    if not issues:
        lines.extend([
            "### ✅ No issues found",
            "",
            "AI Reviewer did not find any issues in this change.",
            "",
            "_Generated by AI Code Review Assistant_",
        ])

        return _truncate_comment(
            "\n".join(lines)
        )

    summary = summarize_issues(issues)

    lines.extend([
        f"Found **{summary['total']} issue(s)**.",
        "",
        "### Severity Summary",
        "",
        "| Severity | Count |",
        "|---|---:|",
    ])

    for severity in SEVERITY_LEVELS + ["UNKNOWN"]:
        lines.append(
            f"| {severity} | {summary[severity]} |"
        )

    lines.append("")

    formatted_count = 0

    for index, issue in enumerate(issues, start=1):
        try:
            issue_markdown = _format_issue(
                issue,
                index,
                repo=repo,
                commit_sha=commit_sha
            )
        except Exception:
            continue

        lines.append(issue_markdown)
        formatted_count += 1

    if formatted_count == 0:
        lines.extend([
            "⚠️ Issues were detected, but their details could not be formatted.",
            "",
        ])

    lines.append(
        "_Generated by AI Code Review Assistant_"
    )

    return _truncate_comment(
        "\n".join(lines)
    )
