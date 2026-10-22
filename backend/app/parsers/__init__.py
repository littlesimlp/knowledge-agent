"""解析器入口：按文件后缀分发。

新增一种格式 = 新增一个模块 + 在 parse_file 里加一个分支，
上层（上传接口）完全不需要改。这就是 D-017 里"可插拔"的具体形态。
"""

from pathlib import Path

from app.parsers.base import ParseResult, ParseStatus
from app.parsers.text import TEXT_SUFFIXES, parse_text

__all__ = ["ParseResult", "ParseStatus", "parse_file"]


def parse_file(path: Path) -> ParseResult:
    """解析一个本地文件，返回统一结构。"""
    if not path.exists():
        return ParseResult(status=ParseStatus.FAILED, message="文件不存在")

    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return parse_text(path)

    supported = "、".join(sorted(TEXT_SUFFIXES))
    return ParseResult(
        status=ParseStatus.UNSUPPORTED,
        message=f"暂不支持 {suffix or '无扩展名'} 文件，当前支持：{supported}",
    )