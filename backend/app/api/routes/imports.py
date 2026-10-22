"""导入接口。

- M2-3：粘贴文本（JSON body）
- M2-4：文件上传（multipart）

两种输入最终都走 app.services.imports.create_entry_with_source，
保证"来源 + 条目 + 关联"的写入规则只有一份。
"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.routes.entries import SessionDep
from app.core.config import settings
from app.models.knowledge_source import SourceType
from app.parsers import parse_file
from app.parsers.base import ParseStatus
from app.parsers.text import TEXT_SUFFIXES
from app.schemas.imports import TextImportRequest, TextImportResult
from app.schemas.knowledge_entry import KnowledgeEntryRead
from app.schemas.knowledge_source import KnowledgeSourceRead
from app.services.imports import create_entry_with_source
from app.services.storage import relative_path, save_upload

router = APIRouter(prefix="/api/imports", tags=["imports"])

# 解析结果不是 OK 时对应的 HTTP 状态码
_PARSE_ERROR_STATUS = {
    ParseStatus.EMPTY: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ParseStatus.UNSUPPORTED: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    ParseStatus.FAILED: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _to_result(entry, source) -> TextImportResult:
    return TextImportResult(
        entry=KnowledgeEntryRead.model_validate(entry),
        source=KnowledgeSourceRead.model_validate(source),
    )


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
    """把一段文本存成来源，并创建一条知识条目，两者建立关联。"""
    entry, source = await create_entry_with_source(
        session,
        source_type=SourceType.PASTED_TEXT,
        source_name=payload.source_name,
        original_text=payload.text,
        title=payload.title,
        content=payload.content,
        source_url=payload.source_url,
        summary=payload.summary,
        category=payload.category,
    )
    return _to_result(entry, source)


@router.post(
    "/file",
    response_model=TextImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="导入文本文件",
)
async def import_file(
    session: SessionDep,
    file: Annotated[UploadFile, File(description=".txt / .md / .markdown 文件")],
    title: Annotated[str | None, Form(description="条目标题，缺省用文件名")] = None,
    category: Annotated[str | None, Form(description="分类")] = None,
) -> TextImportResult:
    """上传一个文本文件：落盘 → 解析 → 建来源与条目 → 建关联。"""
    original_name = file.filename or "unnamed"
    suffix = Path(original_name).suffix.lower()

    if suffix not in TEXT_SUFFIXES:
        supported = "、".join(sorted(TEXT_SUFFIXES))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"暂不支持 {suffix or '无扩展名'} 文件，当前支持：{supported}",
        )

    # 只读"上限 + 1"字节：既能判断是否超限，又不会把超大文件整体读进内存
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"文件超过 {settings.max_upload_bytes // (1024 * 1024)} MB 上限",
        )

    saved = save_upload(data, original_name)
    result = parse_file(saved)

    if result.status is not ParseStatus.OK:
        # 解析失败就删掉刚落的盘，不留垃圾文件
        saved.unlink(missing_ok=True)
        raise HTTPException(
            status_code=_PARSE_ERROR_STATUS.get(
                result.status, status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=result.message or "文件解析失败",
        )

    entry, source = await create_entry_with_source(
        session,
        source_type=SourceType.FILE,
        source_name=original_name,
        original_text=result.text,
        title=title or Path(original_name).stem,
        file_path=relative_path(saved),
        category=category,
    )
    return _to_result(entry, source)