"""AI 整理建议的请求/响应契约。"""

from pydantic import BaseModel, Field, field_validator


class SuggestionRequest(BaseModel):
    """求建议的输入：一段纯文本。"""

    text: str = Field(min_length=1, description="要整理的文本")

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("文本内容不能为空白")
        return stripped


class SuggestionResponse(BaseModel):
    """模型给出的建议。所有内容字段都可能为空——模型有时什么都给不出来。"""

    title: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    # 哪个 provider 生成的：排查问题时非常有用，也让调用方知道当前用的是 fake 还是真实模型
    provider: str