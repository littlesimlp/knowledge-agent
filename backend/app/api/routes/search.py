"""检索接口（M4-1）。"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.routes.entries import SessionDep
from app.schemas.search import SearchHit
from app.services.search import search_entries

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchHit], summary="检索知识条目")
async def search(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=200, description="检索词")],
    keyword: Annotated[
        str | None, Query(max_length=50, description="按关键词精确过滤")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[SearchHit]:
    """按标题/正文子串检索，可选按 `keywords` 精确过滤。

    中文用子串而不是分词：PG 的 simple 配置会把连续中文当成一个 token
    （见 D-025）。`q` 全是空白时返回 422，避免 `%%` 匹配到全部条目。
    """
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="检索词不能为空",
        )

    hits = await search_entries(session, query, keyword=keyword, limit=limit)
    return [SearchHit(entry=entry, snippet=snippet) for entry, snippet in hits]