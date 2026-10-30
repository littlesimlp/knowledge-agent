"""LLM 适配层的公共契约。

业务层只依赖这里的 Protocol 和数据结构——看不到 HTTP、供应商名、
请求/响应格式（设计文档要求：模型供应商格式不应扩散到业务层，见 D-021）。
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EntrySuggestion:
    """对一段文本的整理建议。

    所有字段都可能为空：模型有时什么也给不出来，业务层必须能接受这种情况。
    """

    title: str | None = None
    summary: str | None = None
    keywords: tuple[str, ...] = ()
    category: str | None = None

    def is_empty(self) -> bool:
        return not any((self.title, self.summary, self.keywords, self.category))


class LLMError(Exception):
    """模型调用失败，或返回内容无法使用。

    业务层应当捕获它并降级为手动流程——AI 不是知识库运行的必要条件。
    """


class LLMProvider(Protocol):
    """所有模型提供方都只实现这一个方法。"""

    name: str

    async def suggest_entry(self, text: str) -> EntrySuggestion: ...