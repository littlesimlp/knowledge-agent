"""PDF 文本噪音过滤（D-016）。

只删极可能是页眉/页脚/页码的行，误删正文的风险必须极低：
1. 跨页重复的短行        —— 页眉、页脚、水印
2. 极短的纯数字/符号行   —— 页码

刻意不做的事：不合并空白、不猜段落、不删"看起来像目录"的内容。
"""

import re
from collections.abc import Sequence

# 超过这个长度的行，即使跨页重复也不删（可能是每页都有的长标题/免责声明）
SHORT_LINE_MAX_CHARS = 80

# 出现在至少这个比例的页面上，才算"重复"
REPEAT_PAGE_RATIO = 0.6

# 页码候选：只有数字，外加少量分隔符（如 "1"、"- 12 -"、"第 3 页"里的 3）
_PAGE_NUMBER_RE = re.compile(r"^[\s\-–—·.、/|]*\d{1,4}[\s\-–—·.、/|]*$")


def _lines(page: str) -> list[str]:
    """拆行并去掉首尾空白；保留空行以维持段落结构。"""
    return [line.strip() for line in page.splitlines()]


def find_repeated_short_lines(pages: Sequence[str]) -> set[str]:
    """找出在足够多页面重复出现的短行。"""
    if len(pages) < 2:
        # 只有一页时无法判断"重复"，直接放弃这条规则
        return set()

    counts: dict[str, int] = {}
    for page in pages:
        # 同一页内的重复只算一次，否则纵向铺满的页眉会被放大计数
        for line in set(_lines(page)):
            if line and len(line) <= SHORT_LINE_MAX_CHARS:
                counts[line] = counts.get(line, 0) + 1

    threshold = len(pages) * REPEAT_PAGE_RATIO
    return {line for line, seen in counts.items() if seen >= threshold}


def is_page_number(line: str) -> bool:
    """是否是页码候选：极短的纯数字行。"""
    return bool(line) and bool(_PAGE_NUMBER_RE.match(line))


def clean_pages(pages: Sequence[str]) -> tuple[str, ...]:
    """对每页应用两条规则，返回过滤后的页文本。

    空行保留——PDF 提取出来的空行往往是段落结构的一部分，
    删掉会让整篇挤成一块。
    """
    repeated = find_repeated_short_lines(pages)

    cleaned: list[str] = []
    for page in pages:
        kept = [
            line
            for line in _lines(page)
            if not (line and (line in repeated or is_page_number(line)))
        ]
        cleaned.append("\n".join(kept))
    return tuple(cleaned)