"""问答接口契约（M4-2）。"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    """提问请求。"""

    question: str = Field(min_length=1, max_length=500, description="要问的问题")
    limit: int = Field(default=5, ge=1, le=10, description="检索候选条数")

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("问题不能为空白")
        return stripped


class Citation(BaseModel):
    """一条可核实的引用。"""

    entry_id: uuid.UUID
    title: str
    snippet: str


class AskResponse(BaseModel):
    """回答 + 引用。

    grounded=False 时 answer 是固定话术，citations 必为空——
    前端不能把这时的话术当成"有依据的回答"展示。
    """

    answer: str
    citations: list[Citation]
    grounded: bool
    reason: Literal["ok", "no_results", "ungrounded"]
    provider: str