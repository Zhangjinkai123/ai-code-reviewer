import json
from pathlib import Path


def save_report(result, filename="reports/review-report.json"):

    path = Path(filename)

    path.parent.mkdir(
        exist_ok=True
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result.model_dump(),
            f,
            ensure_ascii=False,
            indent=2
        )


def print_report(result):

    print("\n")
    print("==============================")
    print(" AI Code Review Report")
    print("==============================")


    if not result.issues:

        print("No issues found.")
        return


    for issue in result.issues:

        print("\n----------------")

        print(
            f"File: {issue.file}"
        )

        print(
            f"Line: {issue.line}"
        )

        print(
            f"Severity: {issue.severity}"
        )

        print(
            f"Category: {issue.category}"
        )

        print(
            f"\nIssue:\n{issue.message}"
        )

        print(
            f"\nSuggestion:\n{issue.suggestion}"
        )