"""知识条目的 API 契约（请求体 / 响应体）。

和 ORM 模型分开：ORM 描述"数据库长什么样"，schema 描述"HTTP 接口长什么样"。
两者混用会导致内部字段（如密码、软删除标记）意外暴露给客户端。
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeEntryCreate(BaseModel):
    """创建知识条目的请求体。"""

    title: str = Field(min_length=1, max_length=200, description="标题")
    content: str = Field(min_length=1, description="正文")
    summary: str | None = Field(default=None, description="摘要")
    category: str | None = Field(default=None, max_length=100, description="分类")


class KnowledgeEntryRead(BaseModel):
    """返回给客户端的知识条目。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    content: str
    summary: str | None
    category: str | None
    created_at: datetime
    updated_at: datetime

class KnowledgeEntryUpdate(BaseModel):
    """更新知识条目的请求体。

    所有字段可选：不传 = 不改；传 null = 清空（仅对可空字段有效）。
    这是 PATCH 的语义，区别于 PUT 的"整体替换"。
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    category: str | None = Field(default=None, max_length=100)