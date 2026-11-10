from reviewer.models import Issue, ReviewResult
from reviewer.policy import check_policy, load_policy


POLICY = {
    "review": {
        "severity_threshold": "high",
    }
}


def make_result(severity):

    return ReviewResult(
        issues=[
            Issue(
                file="example.py",
                severity=severity,
                category="test",
                message="test issue",
                suggestion="test suggestion",
            )
        ]
    )


def test_threshold_behavior():

    assert check_policy(
        make_result("low"),
        POLICY,
    )

    assert check_policy(
        make_result("medium"),
        POLICY,
    )

    assert not check_policy(
        make_result("high"),
        POLICY,
    )

    assert not check_policy(
        make_result("critical"),
        POLICY,
    )

    print("[PASS] test_threshold_behavior")


def test_case_insensitive_severity():

    assert not check_policy(
        make_result("HIGH"),
        POLICY,
    )

    print("[PASS] test_case_insensitive_severity")


def test_unknown_severity_rejected():

    try:
        check_policy(
            make_result("unknown"),
            POLICY,
        )
    except ValueError as exc:
        assert "Invalid issue severity" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for unknown severity"
        )

    print("[PASS] test_unknown_severity_rejected")


def test_unknown_severity_after_blocking_issue_rejected():

    result = ReviewResult(
        issues=[
            Issue(
                file="example.py",
                severity="high",
                category="test",
                message="blocking issue",
                suggestion="fix it",
            ),
            Issue(
                file="example.py",
                severity="unknown",
                category="test",
                message="invalid issue",
                suggestion="fix it",
            ),
        ]
    )

    try:
        check_policy(result, POLICY)
    except ValueError as exc:
        assert "Invalid issue severity" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for unknown severity after a blocking issue"
        )

    print("[PASS] test_unknown_severity_after_blocking_issue_rejected")


def test_missing_policy_file_uses_builtin_default():

    import os
    import tempfile

    with tempfile.TemporaryDirectory() as directory:

        missing = os.path.join(directory, "review.yaml")

        policy = load_policy(missing)

    assert policy == {
        "review": {"severity_threshold": "high"}
    }

    # 默认阈值语义必须与原有默认一致：high 阻断。
    assert not check_policy(make_result("high"), policy)
    assert check_policy(make_result("medium"), policy)

    print("[PASS] test_missing_policy_file_uses_builtin_default")


def test_empty_policy_file_uses_builtin_default():

    import os
    import tempfile

    with tempfile.TemporaryDirectory() as directory:

        empty = os.path.join(directory, "review.yaml")

        with open(empty, "w", encoding="utf-8") as f:
            f.write("\n")

        policy = load_policy(empty)

    assert policy == {
        "review": {"severity_threshold": "high"}
    }

    print("[PASS] test_empty_policy_file_uses_builtin_default")


def main():

    test_threshold_behavior()
    test_case_insensitive_severity()
    test_unknown_severity_rejected()
    test_unknown_severity_after_blocking_issue_rejected()
    test_missing_policy_file_uses_builtin_default()
    test_empty_policy_file_uses_builtin_default()

    print()
    print("All policy tests passed.")


if __name__ == "__main__":
    main()
