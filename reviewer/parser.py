import re

from reviewer.models import DiffContext, DiffLine


def parse_diff(diff: str):
    """解析 hunk 内的代码，并仅将完整的新文件标记为完整上下文。"""
    result = []
    context = None
    new_file = False
    old_remaining = new_remaining = 0
    new_line = expected_lines = hunks = 0
    malformed = False

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            context = None
            new_file = False
            old_remaining = new_remaining = 0
        elif line.startswith("--- ") and not (old_remaining or new_remaining):
            new_file = line == "--- /dev/null"
        elif line.startswith("+++ b/") and not (old_remaining or new_remaining):
            context = DiffContext(file=line[6:], lines=[])
            result.append(context)
            expected_lines = hunks = 0
            malformed = False
        elif line.startswith("@@") and context is not None:
            match = re.match(
                r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",
                line,
            )
            if not match:
                context.complete = False
                malformed = True
                continue
            malformed = malformed or bool(old_remaining or new_remaining)
            old_remaining = int(match[2]) if match[2] is not None else 1
            new_line = int(match[3])
            new_remaining = int(match[4]) if match[4] is not None else 1
            expected_lines += new_remaining
            hunks += 1
        elif context is not None and (old_remaining or new_remaining):
            if line.startswith("\\"):
                continue
            if line and line[0] not in " +-":
                context.complete = False
                malformed = True
                continue
            # 兼容历史回归样例中没有空格前缀的空上下文行。
            marker = line[0] if line else " "
            context.lines.append(DiffLine(
                line=new_line,
                content=line[1:],
                type={"+": "add", "-": "remove", " ": "context"}[marker],
            ))
            if marker != "+":
                old_remaining -= 1
            if marker != "-":
                new_remaining -= 1
                new_line += 1
            malformed = malformed or old_remaining < 0 or new_remaining < 0
        elif context is not None and line and line[0] in " +-":
            malformed = True

        if context is not None:
            context.complete = (
                new_file
                and hunks == 1
                and not malformed
                and old_remaining == new_remaining == 0
                and len(context.lines) == expected_lines
                and all(
                    item.type == "add" and item.line == index
                    for index, item in enumerate(context.lines, start=1)
                )
            )

    return result
