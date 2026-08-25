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
from git_utils.diff import get_git_diff



def main():

    if len(sys.argv) < 2:

        print(
            "Usage:"
        )

        print(
            "python main.py demo"
        )

        print(
            "python main.py review"
        )

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



    else:

        print(
            "Unknown command"
        )

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

    if not passed:

        print("\n❌ Review Failed")

        print(
            "Blocking issues detected:"
        )

        for issue in result.issues:

            print(
                f"- {issue.severity}: {issue.category}"
            )

        raise SystemExit(1)

    else:

        print(
            "\nReview Passed"
        )

if __name__ == "__main__":
    # test
    main()