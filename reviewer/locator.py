def locate_line(context, snippet):

    if not snippet:
        return None


    # 去除空白，方便匹配
    snippet_lines = [
        line.strip()
        for line in snippet.splitlines()
        if line.strip()
    ]


    if not snippet_lines:
        return None


    # 遍历 diff 行
    for index, diff_line in enumerate(context.lines):

        current = diff_line.content.strip()


        # 第一行匹配
        if snippet_lines[0] in current:


            # 如果只有一行
            if len(snippet_lines) == 1:
                return str(diff_line.line)


            # 多行匹配
            matched = True


            for offset, target in enumerate(
                snippet_lines[1:],
                start=1
            ):

                next_index = index + offset


                if next_index >= len(context.lines):
                    matched = False
                    break


                next_content = (
                    context.lines[next_index]
                    .content
                    .strip()
                )


                if target not in next_content:
                    matched = False
                    break


            if matched:

                start = diff_line.line

                end = (
                    context.lines[
                        index + len(snippet_lines)-1
                    ].line
                )

                if start == end:
                    return str(start)

                return f"{start}-{end}"


    return None