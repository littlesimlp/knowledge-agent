"""知识来源接口。

条目侧只返回来源元数据（见 `entries.py` 的 `/api/entries/{id}/sources`）；
完整的 `extracted_text` 走这里的详情接口——原文可能有几百 KB，
放进列表响应会让响应体爆炸。
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.routes.entries import SessionDep
from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID
from app.models.knowledge_source import KnowledgeSource
from app.schemas.knowledge_source import KnowledgeSourceDetail

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get(
    "/{source_id}",
    response_model=KnowledgeSourceDetail,
    summary="获取来源详情（含全文）",
)
async def get_source(source_id: uuid.UUID, session: SessionDep) -> KnowledgeSource:
    """按 id 取来源，响应包含完整原文。

    与条目接口一致：不存在或不属于当前空间都返回 404——
    不用 403/404 的差异暴露别的空间里有哪些 id。
    """
    source = await session.get(KnowledgeSource, source_id)
    if source is None or source.workspace_id != DEFAULT_WORKSPACE_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识来源不存在",
        )
    return source
