from reviewer.models import Issue, ReviewResult
from reviewer.formatter import format_review_markdown


def main():
    result = ReviewResult(
        issues=[
            Issue(
                file="UserService.java",
                line="24-25",
                code_snippet=(
                    '"select * from user where id="'
                    "\n"
                    "+ id;"
                ),
                severity="high",
                category="security",
                message=(
                    "id 直接拼接到 SQL 中，"
                    "可能导致 SQL Injection。"
                ),
                suggestion=(
                    "使用参数化查询，例如："
                    'jdbc.queryForObject('
                    '"select * from user where id = ?", '
                    "rowMapper, id)"
                ),
            ),
        ]
    )

    markdown = format_review_markdown(result)

    print("=" * 60)
    print(markdown)
    print("=" * 60)


if __name__ == "__main__":
    main()