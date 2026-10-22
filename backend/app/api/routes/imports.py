"""导入接口。

M2-3 只处理粘贴文本；M2-4 会增加文件上传，复用同一套"来源 + 条目 + 关联"的写入逻辑。
"""

from fastapi import APIRouter, status

from app.api.routes.entries import SessionDep
from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID, KnowledgeEntry
from app.models.knowledge_source import (
    KnowledgeEntrySource,
    KnowledgeSource,
    SourceType,
)
from app.schemas.imports import TextImportRequest, TextImportResult
from app.schemas.knowledge_entry import KnowledgeEntryRead
from app.schemas.knowledge_source import KnowledgeSourceRead

router = APIRouter(prefix="/api/imports", tags=["imports"])

# 原文只保留前 200 字符做展示片段
_EXCERPT_LENGTH = 200


@router.post(
    "/text",
    response_model=TextImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="导入粘贴文本",
)
async def import_text(
    payload: TextImportRequest,
    session: SessionDep,
) -> TextImportResult:
    """把一段文本存成来源，并创建一条知识条目，两者建立关联。

    三个写入必须在同一事务里：来源成功但条目失败会留下孤儿记录。
    add_all + 一次 commit 保证了原子性。
    """
    source = KnowledgeSource(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type=SourceType.PASTED_TEXT.value,
        source_name=payload.source_name,
        source_url=payload.source_url,
        extracted_text=payload.text,
        source_excerpt=payload.text[:_EXCERPT_LENGTH],
    )
    entry = KnowledgeEntry(
        workspace_id=DEFAULT_WORKSPACE_ID,
        title=payload.title,
        content=payload.content or payload.text,
        summary=payload.summary,
        category=payload.category,
    )
    session.add_all([source, entry])

    # flush 让数据库补上 id 和时间戳，之后才能建关联
    await session.flush()
    session.add(KnowledgeEntrySource(entry_id=entry.id, source_id=source.id))

    await session.commit()
    await session.refresh(entry)
    await session.refresh(source)

    return TextImportResult(
        entry=KnowledgeEntryRead.model_validate(entry),
        source=KnowledgeSourceRead.model_validate(source),
    )