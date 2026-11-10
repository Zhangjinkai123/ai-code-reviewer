import json
import os
import tempfile

from reviewer.commenter import load_review_result
from reviewer.models import Issue, ReviewResult
from reviewer.reporter import save_report


def create_result():
    return ReviewResult(
        issues=[
            Issue(
                file="src/UserService.java",
                line="21-24",
                code_snippet=(
                    'String sql = "select * from user where id="'
                    "\n+ id;"
                ),
                severity="high",
                category="security",
                message="存在 SQL 注入风险。",
                suggestion="使用参数化查询。",
            )
        ]
    )


def test_report_round_trip():
    result = create_result()
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".json",
        delete=False,
    )
    temp_file.close()

    try:
        save_report(result, temp_file.name)

        with open(
            temp_file.name,
            encoding="utf-8",
        ) as f:
            raw_data = json.load(f)

        assert raw_data["issues"][0]["message"] == (
            "存在 SQL 注入风险。"
        )

        loaded = load_review_result(temp_file.name)

        assert loaded == result
        assert loaded.issues[0].line == "21-24"
        assert loaded.issues[0].code_snippet.endswith(
            "\n+ id;"
        )

        print("[PASS] test_report_round_trip")

    finally:
        os.unlink(temp_file.name)


def test_empty_report_round_trip():
    result = ReviewResult(issues=[])
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".json",
        delete=False,
    )
    temp_file.close()

    try:
        save_report(result, temp_file.name)
        loaded = load_review_result(temp_file.name)

        assert loaded.issues == []

        print("[PASS] test_empty_report_round_trip")

    finally:
        os.unlink(temp_file.name)


def test_nested_output_directory_created():
    """插件形态下报告可能写到多级目录，必须自动创建。"""
    with tempfile.TemporaryDirectory() as directory:
        target = os.path.join(directory, "a", "b", "c", "report.json")

        save_report(ReviewResult(issues=[]), target)

        assert os.path.exists(target)
        assert load_review_result(target).issues == []

    print("[PASS] test_nested_output_directory_created")


def main():
    test_report_round_trip()
    test_empty_report_round_trip()
    test_nested_output_directory_created()
    print()
    print("All reporter tests passed.")


if __name__ == "__main__":
    main()
