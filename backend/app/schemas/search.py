"""检索响应契约。"""

from pydantic import BaseModel

from app.schemas.knowledge_entry import KnowledgeEntryRead


class SearchHit(BaseModel):
    """一条检索结果：条目 + 命中片段。"""

    entry: KnowledgeEntryRead
    snippet: str