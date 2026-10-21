"""知识条目接口。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID, KnowledgeEntry
from app.schemas.knowledge_entry import KnowledgeEntryCreate, KnowledgeEntryRead

router = APIRouter(prefix="/api/entries", tags=["entries"])


@router.post(
    "",
    response_model=KnowledgeEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建知识条目",
)
async def create_entry(
    payload: KnowledgeEntryCreate,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeEntry:
    entry = KnowledgeEntry(
        **payload.model_dump(),
        workspace_id=DEFAULT_WORKSPACE_ID,
    )
    session.add(entry)
    await session.commit()
    # 必须 refresh：created_at/updated_at 是数据库生成的，
    # commit 后这些字段还没加载，访问它们会触发一次隐式查询 -> 异步下直接报 MissingGreenlet
    await session.refresh(entry)
    return entry


@router.get(
    "",
    response_model=list[KnowledgeEntryRead],
    summary="列出知识条目",
)
async def list_entries(
    session: AsyncSession = Depends(get_session),
) -> list[KnowledgeEntry]:
    result = await session.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.workspace_id == DEFAULT_WORKSPACE_ID)
        .order_by(KnowledgeEntry.created_at.desc())
    )
    return list(result.scalars().all())