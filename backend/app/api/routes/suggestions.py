"""AI 整理建议接口。

**不落库**：只返回建议，用户确认后再走导入接口写入。
这是需求文档"AI 对已有知识的修改必须经用户确认"的直接落地。
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import LLMDep
from app.schemas.suggestions import SuggestionRequest, SuggestionResponse
from app.services.llm.base import LLMError

router = APIRouter(prefix="/api", tags=["suggestions"])


@router.post(
    "/suggestions",
    response_model=SuggestionResponse,
    summary="生成整理建议（不落库）",
)
async def create_suggestion(
    payload: SuggestionRequest,
    llm: LLMDep,
) -> SuggestionResponse:
    """让模型读一段文本，给出标题/摘要/关键词/分类建议。

    AI 失败返回 503 —— 客户端应当降级为手动填写，而不是阻塞用户。
    """
    try:
        suggestion = await llm.suggest_entry(payload.text)
    except LLMError as exc:
        # 503 而不是 500：这是"上游依赖不可用"，是可以重试或降级的情况
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI 暂时不可用：{exc}",
        ) from exc

    return SuggestionResponse(
        title=suggestion.title,
        summary=suggestion.summary,
        keywords=list(suggestion.keywords),
        category=suggestion.category,
        provider=llm.name,
    )