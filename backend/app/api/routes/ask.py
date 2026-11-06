"""问答接口（M4-2）。"""

from fastapi import APIRouter

from app.api.deps import LLMDep, llm_unavailable
from app.api.routes.entries import SessionDep
from app.schemas.ask import AskRequest, AskResponse
from app.services.ask import answer_question
from app.services.llm.base import LLMError

router = APIRouter(prefix="/api", tags=["ask"])


@router.post("/ask", response_model=AskResponse, summary="基于知识库回答问题（带引用）")
async def ask(payload: AskRequest, session: SessionDep, llm: LLMDep) -> AskResponse:
    """检索知识库并让模型作答。

    - 检索为空：200 + `reason=no_results`，不调用模型
    - 引用非法：200 + `reason=ungrounded`，丢弃模型回答
    - 模型失败：503
    """
    try:
        return await answer_question(session, llm, payload.question, limit=payload.limit)
    except LLMError as exc:
        raise llm_unavailable(exc) from exc