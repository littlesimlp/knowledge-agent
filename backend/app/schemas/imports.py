"""导入相关的请求/响应契约。"""

from pydantic import BaseModel, Field, field_validator

from app.schemas.knowledge_entry import KnowledgeEntryRead
from app.schemas.knowledge_source import KnowledgeSourceRead


class TextImportRequest(BaseModel):
    """导入粘贴文本。

    text 是原始输入（进 knowledge_sources.extracted_text），
    content 是用户确认的精炼正文（进 knowledge_entries.content）；
    不传 content 时默认等于原文。
    """

    text: str = Field(min_length=1, description="粘贴的原始文本")
    title: str = Field(min_length=1, max_length=200, description="知识条目标题")
    content: str | None = Field(
        default=None,
        description="精炼后的正文；不传则使用原文",
    )
    source_name: str = Field(
        default="粘贴文本",
        max_length=255,
        description="来源名称，便于日后识别",
    )
    source_url: str | None = Field(default=None, max_length=2048)
    summary: str | None = Field(default=None, description="摘要")
    category: str | None = Field(default=None, max_length=100)

    @field_validator("text")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        """去掉首尾空白后不能为空。

        只在 Field 上写 min_length=1 不够——"   " 也能通过校验。
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("文本内容不能为空白")
        return stripped


class TextImportResult(BaseModel):
    """导入结果：新建的条目 + 来源。"""

    entry: KnowledgeEntryRead
    source: KnowledgeSourceRead