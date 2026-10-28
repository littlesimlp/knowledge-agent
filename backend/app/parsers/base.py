"""解析器基础设施。

解析结果必须能表达四种状态（决策 D-016、D-018）：
上层据此决定"给用户看什么"，而不是把异常直接抛给用户。
"""

from dataclasses import dataclass
from enum import StrEnum


class ParseStatus(StrEnum):
    """解析结果状态。"""

    OK = "ok"                    # 成功，且有文字
    EMPTY = "empty"              # 成功，但没有文字（典型：扫描版 PDF 无文字层）
    UNSUPPORTED = "unsupported"  # 文件类型暂不支持
    FAILED = "failed"            # 解析出错（文件损坏、加密、编码无法识别等）


@dataclass(frozen=True)
class ParseResult:
    """所有解析器的统一返回结构。

    message 是给用户看的中文说明，不是技术堆栈。
    """

    status: ParseStatus
    text: str = ""
    message: str = ""
    page_count: int | None = None
    # 逐页文本，只有 PDF 这类有"页"概念的格式才填；M2-6 的噪音过滤需要它
    pages: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status is ParseStatus.OK