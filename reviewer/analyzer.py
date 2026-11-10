import json

from openai import OpenAI

from reviewer.locator import locate_line
from reviewer.models import ReviewResult, DiffContext
from reviewer.prompt import (
    SYSTEM_PROMPT,
    build_review_input,
)
from reviewer.parser import parse_diff


class _LazyClient:
    """
    延迟创建的 OpenAI client。

    导入模块时不应要求模型配置，否则目标项目缺少 .env 时
    连帮助命令都无法执行。首次访问属性时才读取配置。
    """

    def __init__(self):

        self._client = None

    def _resolve(self):

        if self._client is None:

            import config as config_module

            current = config_module.settings

            self._client = OpenAI(
                api_key=current.OPENAI_API_KEY,
                base_url=current.OPENAI_BASE_URL
            )

        return self._client

    def __getattr__(self, name):

        return getattr(self._resolve(), name)


client = _LazyClient()


def review_code(diff: str):

    # 延迟读取：导入阶段不校验模型配置。
    import config as config_module

    model = config_module.settings.LLM_MODEL

    # 1. 解析 Git diff
    contexts = parse_diff(diff)


    # 2. 转换成 JSON 给 LLM
    review_input = build_review_input(contexts)
    # print("================ LLM INPUT ================")
    # print(review_input)

    response = client.chat.completions.create(

        model=model,

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
    
    result = ReviewResult.model_validate(
        json.loads(
            response.choices[0].message.content
        )
    )

    for issue in result.issues:

        for context in contexts:

            if context.file == issue.file:

                issue.line = locate_line(
                    context,
                    issue.code_snippet
                )


    return result
