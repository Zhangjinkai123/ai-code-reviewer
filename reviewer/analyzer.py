import json

from openai import OpenAI
from config import settings

from reviewer.locator import locate_line
from reviewer.models import ReviewResult, DiffContext
from reviewer.prompt import SYSTEM_PROMPT
from reviewer.parser import parse_diff


client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)


def review_code(diff: str):

    # 1. 解析 Git diff
    contexts = parse_diff(diff)


    # 2. 转换成 JSON 给 LLM
    review_input = json.dumps(
        [
            context.model_dump()
            for context in contexts
        ],
        ensure_ascii=False,
        indent=2
    )
    # print("================ LLM INPUT ================")
    # print(review_input)

    response = client.chat.completions.create(

        model=settings.LLM_MODEL,

        response_format={
            "type": "json_object"
        },

        messages=[
            {
                "role":"system",
                "content":SYSTEM_PROMPT
            },
            {
                "role":"user",
                "content":review_input
            }
        ],

        extra_body={"reasoning": {"enabled": True}}
    )
    
    result = json.loads(
        response.choices[0].message.content
    )

    # print(json.dumps(
    # result,
    # ensure_ascii=False,
    # indent=2
    # ))

    issues = result["issues"]


    for issue in issues:

        for context in contexts:

            if context.file == issue["file"]:

                issue["line"] = locate_line(
                    context,
                    issue.get("code_snippet")
                )


    return ReviewResult(
        issues=issues
    )