"""请求/响应模型包。"""

from app.schemas.imports import TextImportRequest, TextImportResult
from app.schemas.knowledge_entry import (
    KnowledgeEntryCreate,
    KnowledgeEntryRead,
    KnowledgeEntryUpdate,
)
from app.schemas.knowledge_source import KnowledgeSourceRead
from app.schemas.suggestions import SuggestionRequest, SuggestionResponse

__all__ = [
    "KnowledgeEntryCreate",
    "KnowledgeEntryRead",
    "KnowledgeEntryUpdate",
    "KnowledgeSourceRead",
    "SuggestionRequest",
    "SuggestionResponse",
    "TextImportRequest",
    "TextImportResult",
]