"""路由层共享的依赖与辅助函数。

依赖集中在此，路由函数只声明类型；测试用 app.dependency_overrides 替换，
生产代码零改动（和数据库 session 同一套思路）。
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.schemas.suggestions import SuggestionResponse
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMError, LLMProvider

# 业务永远只看到 LLMProvider，看不到具体是哪家模型
LLMDep = Annotated[LLMProvider, Depends(get_llm_provider)]


async def suggest_with_error_mapping(
    llm: LLMProvider,
    text: str,
) -> SuggestionResponse:
    """调用模型，并把失败统一映射成 503。

    两个建议接口（纯文本 / 指定条目）共用这个函数，
    保证"AI 不可用"的错误语义只有一份定义。
    """
    try:
        suggestion = await llm.suggest_entry(text)
    except LLMError as exc:
        # 503 而不是 500：这是"上游依赖不可用"，可以重试或降级
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