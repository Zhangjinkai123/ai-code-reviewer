import os
import sys

from reviewer.analyzer import review_code
from reviewer.reporter import (
    print_report,
    save_report
)
from reviewer.policy import (
    load_policy,
    check_policy
)
from reviewer.formatter import format_review_markdown
from reviewer.github import post_pr_comment
from git_utils.diff import get_git_diff


def print_usage():
    print("Usage:")
    print()
    print("  python main.py demo")
    print("  python main.py review")
    print("  python main.py pr-comment <owner/repository> <pr_number>")


def main():

    if len(sys.argv) < 2:

        print_usage()

        return


    command = sys.argv[1]


    if command == "demo":

        with open(
            "examples/bad_code.diff",
            encoding="utf-8"
        ) as f:

            diff = f.read()


    elif command == "review":

        diff = get_git_diff()


    elif command == "pr-comment":

        if len(sys.argv) < 4:

            print(
                "Usage: "
                "python main.py pr-comment "
                "<owner/repository> <pr_number>"
            )

            raise SystemExit(1)


        repo = sys.argv[2]


        try:

            pr_number = int(sys.argv[3])

        except ValueError:

            print(
                "PR number must be an integer."
            )

            raise SystemExit(1)


        token = os.getenv("GITHUB_TOKEN")


        if not token:

            print(
                "GITHUB_TOKEN environment variable "
                "is not set."
            )

            raise SystemExit(1)


        diff = get_git_diff()


    else:

        print(
            "Unknown command"
        )

        print()

        print_usage()

        return


    if not diff.strip():

        print(
            "No changes detected."
        )

        return


    result = review_code(diff)


    print_report(result)

    save_report(result)


    policy = load_policy()

    passed = check_policy(
        result,
        policy
    )


    # -------------------------------------------------
    # PR Comment
    # -------------------------------------------------

    if command == "pr-comment":

        markdown = format_review_markdown(
            result
        )


        print()
        print(
            "Posting review to GitHub PR..."
        )


        try:

            response = post_pr_comment(
                repo=repo,
                pr_number=pr_number,
                body=markdown,
                token=token
            )


            comment_url = response.get(
                "html_url"
            )


            if comment_url:

                print(
                    f"PR comment created: "
                    f"{comment_url}"
                )

            else:

                print(
                    "PR comment created."
                )


        except Exception as exc:

            print(
                "\n❌ Failed to post "
                "GitHub PR comment"
            )

            print(
                str(exc)
            )

            raise SystemExit(1)


    # -------------------------------------------------
    # Policy
    # -------------------------------------------------

    if not passed:

        print(
            "\n❌ Review Failed"
        )

        print(
            "Blocking issues detected:"
        )


        for issue in result.issues:

            print(
                f"- {issue.severity}: "
                f"{issue.category}"
            )


        raise SystemExit(1)


    else:

        print(
            "\nReview Passed"
        )


if __name__ == "__main__":

    main()