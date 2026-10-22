"""导入业务逻辑。

M2-4 出现第二个调用者（文件导入）时，把"写来源 + 写条目 + 建关联"抽到这里。
这就是 YAGNI 的兑现时点：不是提前抽象，而是重复第二次才抽。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID, KnowledgeEntry
from app.models.knowledge_source import (
    KnowledgeEntrySource,
    KnowledgeSource,
    SourceType,
)

# 原文只保留前 200 字符做展示片段
EXCERPT_LENGTH = 200


async def create_entry_with_source(
    session: AsyncSession,
    *,
    source_type: SourceType,
    source_name: str,
    original_text: str,
    title: str,
    content: str | None = None,
    source_url: str | None = None,
    file_path: str | None = None,
    summary: str | None = None,
    category: str | None = None,
) -> tuple[KnowledgeEntry, KnowledgeSource]:
    """在一个事务里创建来源、条目以及它们的关联。

    三个写入必须原子：来源成功而条目失败会留下孤儿来源。
    """
    source = KnowledgeSource(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type=source_type.value,
        source_name=source_name,
        source_url=source_url,
        file_path=file_path,
        extracted_text=original_text,
        source_excerpt=original_text[:EXCERPT_LENGTH],
    )
    entry = KnowledgeEntry(
        workspace_id=DEFAULT_WORKSPACE_ID,
        title=title,
        content=content or original_text,
        summary=summary,
        category=category,
    )
    session.add_all([source, entry])

    # flush 让数据库补上 id 和时间戳，之后才能建关联
    await session.flush()
    session.add(KnowledgeEntrySource(entry_id=entry.id, source_id=source.id))

    await session.commit()
    await session.refresh(entry)
    await session.refresh(source)
    return entry, source