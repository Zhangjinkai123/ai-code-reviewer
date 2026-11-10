SEVERITY_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}


# 目标项目可以不提供 review.yaml，此时使用内置默认策略。
DEFAULT_POLICY = {
    "review": {
        "severity_threshold": "high"
    }
}



def load_policy(
    filename="review.yaml"
):

    import yaml

    from pathlib import Path

    path = Path(filename)


    # 缺少策略文件不是错误：插件形态下目标项目通常不提供该文件。
    if not path.exists():

        return DEFAULT_POLICY


    with open(
        path,
        encoding="utf-8"
    ) as f:

        policy = yaml.safe_load(f)


    # 空文件同样回落到默认策略，避免后续 .get 失败。
    if policy is None:

        return DEFAULT_POLICY


    return policy




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
