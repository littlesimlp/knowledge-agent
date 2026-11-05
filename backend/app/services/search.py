"""知识检索（M4-1）。

中文没有空格分词：PG 的 simple 配置会把「数据库连接池」当成一个 token，
搜「数据库」匹配不到（实测）。因此用 ILIKE 子串 + pg_trgm GIN 索引，
而不是 to_tsvector。决策见 01-decisions.md 的 D-025。
"""

import re

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID, KnowledgeEntry

_LIKE_ESCAPE = "\\"


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，避免用户输入 `%` 时匹配到全部条目。"""
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", f"{_LIKE_ESCAPE}%")
        .replace("_", f"{_LIKE_ESCAPE}_")
    )


def make_snippet(text: str, query: str, radius: int = 60) -> str:
    """截取命中位置前后的一段，供列表展示。"""
    flat = re.sub(r"\s+", " ", text).strip()
    index = flat.lower().find(query.lower())

    if index < 0:
        head = flat[: radius * 2].strip()
        return head + ("…" if len(flat) > radius * 2 else "")

    start = max(0, index - radius)
    end = min(len(flat), index + len(query) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(flat) else ""
    return f"{prefix}{flat[start:end].strip()}{suffix}"


async def search_entries(
    session: AsyncSession,
    query: str,
    *,
    keyword: str | None = None,
    limit: int = 20,
) -> list[tuple[KnowledgeEntry, str]]:
    """按标题/正文子串检索，可选按 keywords 精确过滤。"""
    pattern = f"%{_escape_like(query)}%"
    title_hit = KnowledgeEntry.title.ilike(pattern, escape=_LIKE_ESCAPE)

    stmt = (
        select(KnowledgeEntry)
        .where(
            KnowledgeEntry.workspace_id == DEFAULT_WORKSPACE_ID,
            or_(
                title_hit,
                KnowledgeEntry.content.ilike(pattern, escape=_LIKE_ESCAPE),
            ),
        )
        .order_by(title_hit.desc(), KnowledgeEntry.updated_at.desc())
        .limit(limit)
    )

    if keyword:
        stmt = stmt.where(KnowledgeEntry.keywords.contains([keyword]))

    entries = list((await session.execute(stmt)).scalars().all())
    return [(entry, make_snippet(entry.content, query)) for entry in entries]