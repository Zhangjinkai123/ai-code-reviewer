import re

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

from reviewer.models import DiffContext


def _is_yaml_file(filename: str) -> bool:
    return filename.lower().endswith((".yml", ".yaml"))


def _format_path(parts: tuple[object, ...]) -> str:
    path = "$"

    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", str(part)):
            path += f".{part}"
        else:
            path += f"[{part!r}]"

    return path


def _collect_key_paths(
    node,
    line_numbers,
    path=(),
    ancestors=frozenset(),
):
    entries = []

    if id(node) in ancestors:
        return entries
    ancestors = ancestors | {id(node)}

    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                continue

            key = str(key_node.value)
            current_path = (*path, key)
            line_index = key_node.start_mark.line

            if line_index < len(line_numbers):
                entries.append(
                    {
                        "line": line_numbers[line_index],
                        "key": key,
                        "path": _format_path(current_path),
                    }
                )

            entries.extend(
                _collect_key_paths(
                    value_node,
                    line_numbers,
                    current_path,
                    ancestors,
                )
            )

    elif isinstance(node, SequenceNode):
        for index, item_node in enumerate(node.value):
            entries.extend(
                _collect_key_paths(
                    item_node,
                    line_numbers,
                    (*path, index),
                    ancestors,
                )
            )

    return entries


def build_yaml_context(context: DiffContext) -> dict | None:
    """
    为 YAML Diff 提供可供 LLM 参考的结构化上下文。

    只使用新增行和上下文行重建输入。对于局部 Diff，解析失败或
    结构不完整时不作确定性判断，避免把缺失上下文误当成配置错误。
    """
    if not _is_yaml_file(context.file):
        return None

    records = [
        line
        for line in context.lines
        if line.type != "remove"
    ]

    if not records:
        return {
            "parse_status": "unavailable",
            "complete": False,
            "key_paths": [],
        }

    line_numbers = [line.line for line in records]
    is_contiguous = all(
        current == previous + 1
        for previous, current in zip(line_numbers, line_numbers[1:])
    )
    is_complete = (
        context.complete
        and line_numbers[0] == 1
        and is_contiguous
        and all(line.type == "add" for line in records)
    )

    yaml_text = "\n".join(
        line.content
        for line in records
    )

    try:
        document = yaml.compose(yaml_text, Loader=yaml.SafeLoader)
        key_paths = (
            _collect_key_paths(document, line_numbers)
            if is_complete
            else []
        )
    except (yaml.YAMLError, RecursionError):
        return {
            "parse_status": "invalid" if is_complete else "unavailable",
            "complete": is_complete,
            "key_paths": [],
        }

    if document is None:
        return {
            "parse_status": "valid",
            "complete": is_complete,
            "key_paths": [],
        }

    return {
        "parse_status": "valid",
        "complete": is_complete,
        "key_paths": key_paths,
    }
