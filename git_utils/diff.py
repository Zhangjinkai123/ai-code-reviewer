import os
import subprocess


def _resolve_default_base():

    candidates = []

    symbolic_ref = subprocess.run(
        [
            "git",
            "symbolic-ref",
            "--quiet",
            "--short",
            "refs/remotes/origin/HEAD",
        ],
        capture_output=True,
        text=True,
    )

    if symbolic_ref.returncode == 0:

        ref = symbolic_ref.stdout.strip()

        if ref:
            candidates.append(ref)

    candidates.extend(
        [
            "origin/master",
            "origin/main",
        ]
    )

    checked = set()

    for ref in candidates:

        if ref in checked:
            continue

        checked.add(ref)

        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "--verify",
                f"{ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return ref

    raise RuntimeError(
        "Unable to resolve the default Git base branch. "
        "Expected origin/HEAD, origin/master, or origin/main."
    )



def get_git_diff():

    base_sha = os.getenv(
        "GITHUB_BASE_SHA"
    )


    if base_sha:

        cmd = [
            "git",
            "diff",
            base_sha,
            "HEAD"
        ]


    else:

        base_ref = _resolve_default_base()

        cmd = [
            "git",
            "diff",
            base_ref,
        ]



    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )


    if result.returncode != 0:

        raise RuntimeError(
            result.stderr
        )


    return result.stdout
