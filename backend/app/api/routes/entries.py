"""知识条目接口。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID, KnowledgeEntry
from app.schemas.knowledge_entry import (
    KnowledgeEntryCreate,
    KnowledgeEntryRead,
    KnowledgeEntryUpdate,
)

router = APIRouter(prefix="/api/entries", tags=["entries"])


async def _get_entry_or_404(
    entry_id: uuid.UUID,
    session: AsyncSession,
) -> KnowledgeEntry:
    """按 id 取条目；不存在或不属于当前空间时一律返回 404。

    故意不区分"不存在"和"存在但无权访问"——否则通过 403/404 的差异
    就能探测出别的空间里有哪些 id。
    """
    entry = await session.get(KnowledgeEntry, entry_id)
    if entry is None or entry.workspace_id != DEFAULT_WORKSPACE_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在",
        )
    return entry


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
    # 必须 refresh：created_at/updated_at 是数据库端生成的，
    # 不 refresh 就取不到值（异步下会抛 MissingGreenlet）
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


@router.get(
    "/{entry_id}",
    response_model=KnowledgeEntryRead,
    summary="获取单条知识条目",
)
async def get_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeEntry:
    return await _get_entry_or_404(entry_id, session)


@router.patch(
    "/{entry_id}",
    response_model=KnowledgeEntryRead,
    summary="更新知识条目",
)
async def update_entry(
    entry_id: uuid.UUID,
    payload: KnowledgeEntryUpdate,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeEntry:
    entry = await _get_entry_or_404(entry_id, session)

    # exclude_unset=True：只处理客户端真正传了的字段，
    # 没传的字段保持原值。不加这个参数会把所有 None 写进去。
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)

    await session.commit()
    # updated_at 是数据库端 onupdate 生成的，必须 refresh 才能拿到新值
    await session.refresh(entry)
    return entry


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除知识条目",
)
async def delete_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    entry = await _get_entry_or_404(entry_id, session)
    await session.delete(entry)
    await session.commit()