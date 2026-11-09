import json
from pathlib import Path

import yaml

from reviewer.parser import parse_diff
from reviewer.prompt import (
    SYSTEM_PROMPT,
    build_review_input,
)
from reviewer.yaml_context import build_yaml_context


EXAMPLES = Path("examples")


def load_context(filename):
    diff = (EXAMPLES / filename).read_text(
        encoding="utf-8"
    )
    contexts = parse_diff(diff)

    assert len(contexts) == 1
    assert contexts[0].file == ".github/workflows/test.yml"

    return contexts[0]


def test_yaml_samples_are_syntax_valid():
    for filename in (
        "yaml_regression_valid.diff",
        "yaml_regression_invalid.diff",
    ):
        context = load_context(filename)
        yaml_text = "\n".join(
            line.content
            for line in context.lines
            if line.type != "remove"
        )

        assert yaml.safe_load(yaml_text) is not None

    print("[PASS] YAML samples are syntactically valid")


def test_yaml_paths_distinguish_valid_and_invalid_layout():
    valid = build_yaml_context(
        load_context("yaml_regression_valid.diff")
    )
    invalid = build_yaml_context(
        load_context("yaml_regression_invalid.diff")
    )

    assert valid["parse_status"] == "valid"
    assert valid["complete"] is True
    assert invalid["parse_status"] == "valid"
    assert invalid["complete"] is True

    valid_commit_path = next(
        item["path"]
        for item in valid["key_paths"]
        if item["key"] == "COMMIT_SHA"
    )
    invalid_commit_path = next(
        item["path"]
        for item in invalid["key_paths"]
        if item["key"] == "COMMIT_SHA"
    )

    assert valid_commit_path == (
        "$.jobs.comment.steps[0].env.COMMIT_SHA"
    )
    assert invalid_commit_path == (
        "$.jobs.comment.steps[0].COMMIT_SHA"
    )

    print("[PASS] YAML paths distinguish valid and invalid layout")


def test_review_input_keeps_yaml_structure_metadata():
    valid_context = load_context(
        "yaml_regression_valid.diff"
    )
    review_input = json.loads(
        build_review_input([valid_context])
    )

    item = review_input[0]

    assert item["yaml_context"]["complete"] is True
    assert item["yaml_context"]["parse_status"] == "valid"
    assert any(
        line["content"].strip() == "COMMIT_SHA: ${{ github.event.workflow_run.head_sha }}"
        and line["indent"] == 10
        for line in item["lines"]
    )
    assert (
        "$.jobs.comment.steps[0].env.COMMIT_SHA"
        in {
            key["path"]
            for key in item["yaml_context"]["key_paths"]
        }
    )

    print("[PASS] Review input keeps YAML structure metadata")


def test_partial_yaml_diff_does_not_claim_complete_paths():
    context = load_context(
        "yaml_regression_valid.diff"
    ).model_copy(
        update={
            "lines": [
                line.model_copy(
                    update={
                        "line": line.line + 10
                    }
                )
                for line in load_context(
                    "yaml_regression_valid.diff"
                ).lines
            ]
        }
    )

    yaml_context = build_yaml_context(context)

    assert yaml_context["complete"] is False
    assert yaml_context["key_paths"] == []

    print("[PASS] Partial YAML diff does not claim complete paths")


def test_prompt_requires_schema_and_context_confirmation():
    required_rules = [
        "不得仅凭视觉上的缩进差异判断 YAML 配置错误",
        "jobs.<job>.steps[*]",
        "COMMIT_SHA",
        "返回空 `issues`",
    ]

    for rule in required_rules:
        assert rule in SYSTEM_PROMPT

    print("[PASS] Prompt requires schema and context confirmation")


def test_existing_file_addition_is_not_complete():
    diff = (
        "--- a/test.yml\n+++ b/test.yml\n"
        "@@ -0,0 +1,2 @@\n+name: test\n+jobs: {}\n"
    )
    context = parse_diff(diff)[0]
    assert context.complete is False
    assert build_yaml_context(context)["key_paths"] == []


def test_context_indentation_and_hunk_boundaries():
    diff = (
        "diff --git a/test.yml b/test.yml\n"
        "--- a/test.yml\n+++ b/test.yml\n"
        "@@ -1,3 +1,3 @@\n"
        " env:\n-  OLD: value\n+  NEW: value\n"
        "   KEEP: value\n"
        "\\ No newline at end of file\n"
        "diff --git a/other.yml b/other.yml\n"
        "new file mode 100644\n--- /dev/null\n+++ b/other.yml\n"
        "@@ -0,0 +1 @@\n+name: other\n"
    )
    first, second = parse_diff(diff)
    assert [line.content for line in first.lines] == [
        "env:", "  OLD: value", "  NEW: value", "  KEEP: value",
    ]
    assert [line.line for line in first.lines] == [1, 2, 2, 3]
    assert first.complete is False
    assert second.complete is True
    item = json.loads(build_review_input([first]))[0]
    assert [line["indent"] for line in item["lines"]] == [0, 2, 2, 2]


def test_new_file_completeness_and_recursive_alias():
    prefix = "--- /dev/null\n+++ b/test.yml\n"
    for hunk in (
        "@@ -0,0 +1,2 @@\n+name: test\n",
        "@@ -0,0 +1,2 @@\n+name: test\n+jobs: {}\n+extra: value\n",
    ):
        context = parse_diff(prefix + hunk)[0]
        assert context.complete is False
    context = parse_diff(
        prefix + "@@ -0,0 +1 @@\n+root: &root {self: *root}\n"
    )[0]
    metadata = build_yaml_context(context)
    assert metadata["parse_status"] == "valid"
    assert [item["path"] for item in metadata["key_paths"]] == [
        "$.root", "$.root.self",
    ]
    second = prefix.replace("test.yml", "other.yml")
    contexts = parse_diff(
        "diff --git a/test.yml b/test.yml\n"
        + prefix + "@@ -0,0 +1 @@\n+name: first\n"
        + "diff --git a/other.yml b/other.yml\n"
        + second + "@@ -0,0 +1 @@\n+name: second\n"
    )
    assert len(contexts) == 2
    assert all(context.complete for context in contexts)


def test_complete_invalid_yaml_and_partial_invalid_yaml():
    diff = "--- /dev/null\n+++ b/test.yml\n@@ -0,0 +1 @@\n+root: [\n"
    context = parse_diff(diff)[0]
    assert build_yaml_context(context)["parse_status"] == "invalid"
    context.complete = False
    assert build_yaml_context(context)["parse_status"] == "unavailable"


def test_alias_expansion_has_a_shared_budget():
    lines = ["root: &level0 {leaf: value}"]
    for index in range(1, 24):
        lines.append(
            f"level{index}: &level{index} "
            f"[*level{index - 1}, *level{index - 1}]"
        )
    diff = (
        "--- /dev/null\n+++ b/test.yml\n"
        f"@@ -0,0 +1,{len(lines)} @@\n"
        + "\n".join("+" + line for line in lines)
    )
    context = parse_diff(diff)[0]
    assert context.complete is True
    metadata = build_yaml_context(context)
    assert metadata == {
        "parse_status": "unavailable",
        "complete": False,
        "key_paths": [],
        "reason": "structure_limit",
    }
    payload = json.loads(build_review_input([context]))
    assert payload[0]["yaml_context"] == metadata
    print("[PASS] YAML alias expansion is bounded")


def main():
    test_yaml_samples_are_syntax_valid()
    test_yaml_paths_distinguish_valid_and_invalid_layout()
    test_review_input_keeps_yaml_structure_metadata()
    test_partial_yaml_diff_does_not_claim_complete_paths()
    test_prompt_requires_schema_and_context_confirmation()
    test_existing_file_addition_is_not_complete()
    test_context_indentation_and_hunk_boundaries()
    test_new_file_completeness_and_recursive_alias()
    test_complete_invalid_yaml_and_partial_invalid_yaml()
    test_alias_expansion_has_a_shared_budget()
    print()
    print("All YAML regression tests passed.")


if __name__ == "__main__":
    main()
