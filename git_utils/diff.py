import os
import subprocess


def _git_command(repo_dir, *args):
    """构造 git 命令；指定 repo_dir 时用 -C，否则保持原有行为。"""

    if repo_dir:

        return ["git", "-C", str(repo_dir), *args]

    return ["git", *args]


def _resolve_default_base(repo_dir=None):

    candidates = []

    symbolic_ref = subprocess.run(
        _git_command(
            repo_dir,
            "symbolic-ref",
            "--quiet",
            "--short",
            "refs/remotes/origin/HEAD",
        ),
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
            _git_command(
                repo_dir,
                "rev-parse",
                "--verify",
                f"{ref}^{{commit}}",
            ),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return ref

    raise RuntimeError(
        "Unable to resolve the default Git base branch. "
        "Expected origin/HEAD, origin/master, or origin/main."
    )



def get_git_diff(repo_dir=None):

    base_sha = os.getenv(
        "GITHUB_BASE_SHA"
    )


    if base_sha:

        cmd = _git_command(
            repo_dir,
            "diff",
            base_sha,
            "HEAD"
        )


    else:

        base_ref = _resolve_default_base(repo_dir)

        merge_base = subprocess.run(
            _git_command(
                repo_dir,
                "merge-base",
                base_ref,
                "HEAD",
            ),
            capture_output=True,
            text=True,
        )

        if merge_base.returncode != 0:
            raise RuntimeError(
                merge_base.stderr
                or (
                    "Unable to resolve the common ancestor "
                    "between the default base and HEAD."
                )
            )

        merge_base_sha = merge_base.stdout.strip()

        if not merge_base_sha:
            raise RuntimeError(
                "Unable to resolve the common ancestor "
                "between the default base and HEAD."
            )

        cmd = _git_command(
            repo_dir,
            "diff",
            merge_base_sha,
        )



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
