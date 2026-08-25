from reviewer.parser import parse_diff


with open(
    "examples/bad_code.diff",
    encoding="utf-8"
) as f:

    diff = f.read()


result = parse_diff(diff)


for item in result:
    print(item)