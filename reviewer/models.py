from pydantic import BaseModel
from typing import List

class DiffLine(BaseModel):

    line: int

    content: str

    type: str
    # add / remove / context

class DiffContext(BaseModel):

    file: str

    lines: List[DiffLine]

class Issue(BaseModel):

    file: str = "unknown"

    line: str | None = None

    #   代码片段
    code_snippet: str | None = None

    #   严重程度
    severity: str

    category: str

    message: str

    suggestion: str


class ReviewResult(BaseModel):

    issues: List[Issue]