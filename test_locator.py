from reviewer.locator import locate_line
from reviewer.parser import parse_diff


def load_context():
    with open(
        "examples/bad_code.diff",
        encoding="utf-8",
    ) as f:
        contexts = parse_diff(f.read())

    assert len(contexts) == 1
    return contexts[0]


def test_single_line_match():
    context = load_context()

    assert locate_line(
        context,
        "public User getUser(String id){",
    ) == "21"


def test_multi_line_match():
    context = load_context()
    snippet = (
        '"select * from user where id="\n'
        "+ id;"
    )

    matching_index = next(
        index
        for index, line in enumerate(context.lines[:-1])
        if '"select * from user where id="'
        in line.content
        and "+ id;" in context.lines[index + 1].content
    )

    expected = (
        f"{context.lines[matching_index].line}-"
        f"{context.lines[matching_index + 1].line}"
    )

    assert locate_line(context, snippet) == expected


def test_empty_and_missing_snippets():
    context = load_context()

    assert locate_line(context, "") is None
    assert locate_line(context, " \n ") is None
    assert locate_line(context, "code that is not in the diff") is None


def main():
    test_single_line_match()
    test_multi_line_match()
    test_empty_and_missing_snippets()
    print("Locator assertions passed.")


if __name__ == "__main__":
    main()
