"""知识来源与关联表。

设计文档要求：一份来源可以支持多个知识条目，一个知识条目也可以关联多个来源，
所以用一张关联表表达多对多。

决策 D-016：原文与精炼正文分离存储——
knowledge_sources.extracted_text 保存解析器产出的完整文本快照，
knowledge_entries.content 只保存用户确认后的精炼版。
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID


class SourceType(StrEnum):
    """来源类型。

    用 Python 枚举做类型安全，数据库里存 VARCHAR 而不是原生 enum：
    原生 enum 增加取值需要 ALTER TYPE，迁移麻烦；VARCHAR + 应用层校验更灵活。
    """

    FILE = "file"
    PASTED_TEXT = "pasted_text"
    URL = "url"


class KnowledgeEntrySource(Base):
    """知识条目 ↔ 来源 的多对多关联表。"""

    __tablename__ = "knowledge_entry_sources"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_entries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        primary_key=True,
    )


class KnowledgeSource(Base):
    """一条知识来源。原始输入必须可追溯，所以这个表是权威记录。"""

    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        default=DEFAULT_WORKSPACE_ID,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # 文件在宿主机上的相对路径；文件本身不存数据库
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # 解析器提取出的完整文本快照（决策 D-016）。可空：粘贴文本 / URL 类型可能没有
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 展示用的短片段，避免详情页拉取整篇原文
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeSource {self.id} {self.source_type} {self.source_name!r}>"