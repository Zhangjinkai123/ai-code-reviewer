import subprocess


def get_git_diff():
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr
        )


    return result.stdout