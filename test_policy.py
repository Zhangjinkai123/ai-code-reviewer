from reviewer.models import Issue, ReviewResult
from reviewer.policy import check_policy


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


def main():

    test_threshold_behavior()
    test_case_insensitive_severity()
    test_unknown_severity_rejected()
    test_unknown_severity_after_blocking_issue_rejected()

    print()
    print("All policy tests passed.")


if __name__ == "__main__":
    main()
