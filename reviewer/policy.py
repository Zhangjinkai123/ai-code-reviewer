SEVERITY_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}



def load_policy(
    filename="review.yaml"
):

    import yaml

    with open(
        filename,
        encoding="utf-8"
    ) as f:

        return yaml.safe_load(f)




def check_policy(
    result,
    policy
):

    review_config = (
        policy
        .get(
            "review",
            {}
        )
    )


    threshold = (
        review_config
        .get(
            "severity_threshold",
            "high"
        )
    )

    if isinstance(threshold, str):
        threshold = threshold.strip().lower()
    
    def validate_threshold(threshold):

        if threshold not in SEVERITY_LEVELS:

            raise ValueError(
                f"Invalid severity threshold: {threshold}"
            )

    validate_threshold(threshold)

    threshold_level = (
        SEVERITY_LEVELS
        .get(
            threshold,
            3
        )
    )


    has_blocking_issue = False

    for issue in result.issues:

        severity = issue.severity

        if not isinstance(severity, str):
            raise ValueError(
                f"Invalid issue severity: {severity}"
            )

        severity = severity.strip().lower()

        if severity not in SEVERITY_LEVELS:
            raise ValueError(
                f"Invalid issue severity: {issue.severity}"
            )

        issue_level = SEVERITY_LEVELS[severity]


        if issue_level >= threshold_level:

            has_blocking_issue = True

    return not has_blocking_issue
