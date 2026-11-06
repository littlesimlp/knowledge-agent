"""问答编排（M4-2）。

流程：检索候选 → 为空则直接兜底（不调模型）→ 拼编号资料 → 调模型 →
校验引用编号 → 映射成 Citation。

两条硬规则：
1. 检索为空时不调用模型（省钱，也避免编造）；
2. 引用编号必须落在候选范围内，否则整段回答降级为固定话术。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_entry import KnowledgeEntry
from app.schemas.ask import AskResponse, Citation
from app.services.llm.base import LLMProvider
from app.services.search import search_entries

NO_RESULTS_ANSWER = "知识库中没有找到相关内容。"
UNGROUNDED_ANSWER = "找到了相关资料，但没能生成可核实的引用，因此不展示回答。"

# 单条资料进 prompt 的字符上限，避免 5 条长文挤掉问题
_CONTEXT_CHARS = 1500


def _format_context(index: int, entry: KnowledgeEntry) -> str:
    content = (entry.content or "").strip()
    if len(content) > _CONTEXT_CHARS:
        content = content[:_CONTEXT_CHARS] + "…"
    return f"[{index}] 标题：{entry.title}\n内容：{content}"


async def answer_question(
    session: AsyncSession,
    llm: LLMProvider,
    question: str,
    *,
    limit: int = 5,
) -> AskResponse:
    """检索 + 生成 + 引用校验。"""
    hits = await search_entries(session, question, limit=limit)
    if not hits:
        return AskResponse(
            answer=NO_RESULTS_ANSWER,
            citations=[],
            grounded=False,
            reason="no_results",
            provider=llm.name,
        )

    contexts = [
        _format_context(index, entry)
        for index, (entry, _snippet) in enumerate(hits, start=1)
    ]
    draft = await llm.answer(question, contexts)

    valid_numbers = {index for index in range(1, len(hits) + 1)}
    citations: list[Citation] = []
    seen: set[int] = set()
    for number in draft.citation_numbers:
        # 重复编号只保留一次：这是 service 的契约，不依赖 provider 去重
        if number not in valid_numbers or number in seen:
            continue
        seen.add(number)
        entry, snippet = hits[number - 1]
        citations.append(
            Citation(entry_id=entry.id, title=entry.title, snippet=snippet)
        )

    if not citations:
        return AskResponse(
            answer=UNGROUNDED_ANSWER,
            citations=[],
            grounded=False,
            reason="ungrounded",
            provider=llm.name,
        )

    return AskResponse(
        answer=draft.answer,
        citations=citations,
        grounded=True,
        reason="ok",
        provider=llm.name,
    )