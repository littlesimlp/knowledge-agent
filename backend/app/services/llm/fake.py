"""测试与本地开发用的假实现：不联网、结果确定。"""

from app.services.llm.base import EntrySuggestion, LLMError


class FakeProvider:
    """返回预设建议，或者按预设抛错。"""

    name = "fake"

    def __init__(
        self,
        suggestion: EntrySuggestion | None = None,
        error: LLMError | None = None,
    ) -> None:
        self._suggestion = suggestion or EntrySuggestion(
            title="示例标题",
            summary="示例摘要",
            keywords=("示例", "测试"),
            category="示例分类",
        )
        self._error = error

    async def suggest_entry(self, text: str) -> EntrySuggestion:
        if self._error is not None:
            raise self._error
        return self._suggestion