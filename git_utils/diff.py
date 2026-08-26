import os
import subprocess



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

        cmd = [
            "git",
            "diff",
            "origin/main..."
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