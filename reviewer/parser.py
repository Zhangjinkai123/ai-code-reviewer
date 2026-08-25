import re

from reviewer.models import (
    DiffContext,
    DiffLine
)



def parse_diff(diff: str):

    result = []

    current_file = None

    current_lines = []

    current_new_line = None



    for line in diff.splitlines():


        # 文件名
        if line.startswith("+++ b/"):


            if current_file:

                result.append(
                    DiffContext(
                        file=current_file,
                        lines=current_lines
                    )
                )


            current_file = line.replace(
                "+++ b/",
                ""
            )

            current_lines = []



        # hunk信息
        elif line.startswith("@@"):


            match = re.search(
                r"\+(\d+)",
                line
            )


            if match:

                current_new_line = int(
                    match.group(1)
                )



        elif current_file and current_new_line:


            # 新增代码
            if line.startswith("+") and not line.startswith("+++"):

                current_lines.append(
                    DiffLine(
                        line=current_new_line,
                        content=line[1:],
                        type="add"
                    )
                )


                current_new_line += 1



            # 删除代码
            elif line.startswith("-") and not line.startswith("---"):

                current_lines.append(
                    DiffLine(
                        line=current_new_line,
                        content=line[1:],
                        type="remove"
                    )
                )



            # 上下文代码
            else:

                current_lines.append(
                    DiffLine(
                        line=current_new_line,
                        content=line,
                        type="context"
                    )
                )


                current_new_line += 1




    if current_file:

        result.append(
            DiffContext(
                file=current_file,
                lines=current_lines
            )
        )


    return result