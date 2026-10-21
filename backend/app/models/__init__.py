"""ORM 模型包。

新增模型后必须在这里导入，否则 Alembic 的 autogenerate 看不到它。
"""

from app.models.knowledge_entry import KnowledgeEntry

__all__ = ["KnowledgeEntry"]