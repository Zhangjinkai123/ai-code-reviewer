from reviewer.parser import parse_diff


with open(
    "examples/bad_code.diff",
    encoding="utf-8"
) as f:

    diff = f.read()


result = parse_diff(diff)

assert len(result) == 1

context = result[0]

assert context.file == "UserService.java"
assert context.lines[0].line == 15
assert context.lines[0].type == "context"
assert context.lines[6].line == 21
assert context.lines[6].type == "add"
assert context.lines[6].content == (
    "    public User getUser(String id){"
)
assert context.lines[-1].line == 30
assert context.lines[-1].type == "context"

print("Parser assertions passed.")
