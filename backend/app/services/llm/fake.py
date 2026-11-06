"""测试与本地开发用的假实现：不联网、结果确定。"""

from collections.abc import Sequence

from app.services.llm.base import AnswerDraft, EntrySuggestion, LLMError


class FakeProvider:
    """返回预设结果，或者按预设抛错。"""

    name = "fake"

    def __init__(
        self,
        suggestion: EntrySuggestion | None = None,
        error: LLMError | None = None,
        answer: AnswerDraft | None = None,
    ) -> None:
        self._suggestion = suggestion or EntrySuggestion(
            title="示例标题",
            summary="示例摘要",
            keywords=("示例", "测试"),
            category="示例分类",
        )
        self._error = error
        self._answer = answer or AnswerDraft(
            answer="示例回答",
            citation_numbers=(1,),
        )

    async def suggest_entry(self, text: str) -> EntrySuggestion:
        if self._error is not None:
            raise self._error
        return self._suggestion

    async def answer(self, question: str, contexts: Sequence[str]) -> AnswerDraft:
        if self._error is not None:
            raise self._error
        return self._answer