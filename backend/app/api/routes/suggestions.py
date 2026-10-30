"""AI 整理建议接口。

**不落库**：只返回建议，用户确认后再写入。
这是需求文档"AI 对已有知识的修改必须经用户确认"的直接落地。
"""

from fastapi import APIRouter

from app.api.deps import LLMDep, suggest_with_error_mapping
from app.schemas.suggestions import SuggestionRequest, SuggestionResponse

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
    """让模型读一段纯文本，给出标题/摘要/关键词/分类建议。

    AI 失败返回 503 —— 客户端应降级为手动填写，而不是阻塞用户。
    """
    return await suggest_with_error_mapping(llm, payload.text)