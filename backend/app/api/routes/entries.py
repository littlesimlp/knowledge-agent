"""知识条目接口。"""

import uuid
from typing import Annotated

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
from app.services.entries import delete_entry_cascade, remove_files

router = APIRouter(prefix="/api/entries", tags=["entries"])

# FastAPI 官方推荐的依赖声明方式。
# 相比 session: AsyncSession = Depends(get_session)，Annotated 不会触发 B008
# （"默认参数里不要调用函数"），并且类型信息对编辑器更友好。
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_entry_or_404(
    entry_id: uuid.UUID,
    session: AsyncSession,
) -> KnowledgeEntry:
    """按 id 取条目；不存在或不属于当前空间时一律返回 404。

    故意不区分「不存在」和「存在但无权访问」——否则通过 403/404 的差异
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
    session: SessionDep,
) -> KnowledgeEntry:
    entry = KnowledgeEntry(
        **payload.model_dump(),
        workspace_id=DEFAULT_WORKSPACE_ID,
    )
    session.add(entry)
    await session.commit()
    # 必须 refresh：created_at/updated_at 是数据库端生成的
    await session.refresh(entry)
    return entry


@router.get(
    "",
    response_model=list[KnowledgeEntryRead],
    summary="列出知识条目",
)
async def list_entries(session: SessionDep) -> list[KnowledgeEntry]:
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
async def get_entry(entry_id: uuid.UUID, session: SessionDep) -> KnowledgeEntry:
    return await _get_entry_or_404(entry_id, session)


@router.patch(
    "/{entry_id}",
    response_model=KnowledgeEntryRead,
    summary="更新知识条目",
)
async def update_entry(
    entry_id: uuid.UUID,
    payload: KnowledgeEntryUpdate,
    session: SessionDep,
) -> KnowledgeEntry:
    entry = await _get_entry_or_404(entry_id, session)

    # exclude_unset=True：只处理客户端真正传了的字段
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
async def delete_entry(entry_id: uuid.UUID, session: SessionDep) -> None:
    """删除条目，并连带删除无其它条目引用的来源及其磁盘文件（D-020）。"""
    entry = await _get_entry_or_404(entry_id, session)

    # service 内部完成数据库事务；返回需要在提交后删除的文件
    orphan_files = await delete_entry_cascade(session, entry)

    # 事务已提交，现在可以安全删文件（失败只记日志）
    remove_files(orphan_files)