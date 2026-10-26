"""解析器入口：按文件后缀分发。

新增一种格式 = 新增一个模块 + 在 parse_file 里加一个分支，上层不需要改。
"""

from pathlib import Path

from app.parsers.base import ParseResult, ParseStatus
from app.parsers.pdf import PDF_SUFFIXES, parse_pdf
from app.parsers.text import TEXT_SUFFIXES, parse_text

__all__ = ["SUPPORTED_SUFFIXES", "ParseResult", "ParseStatus", "parse_file"]

# 上传接口用这个做白名单校验
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | PDF_SUFFIXES


def parse_file(path: Path) -> ParseResult:
    """解析一个本地文件，返回统一结构。"""
    if not path.exists():
        return ParseResult(status=ParseStatus.FAILED, message="文件不存在")

    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return parse_text(path)
    if suffix in PDF_SUFFIXES:
        return parse_pdf(path)

    supported = "、".join(sorted(SUPPORTED_SUFFIXES))
    return ParseResult(
        status=ParseStatus.UNSUPPORTED,
        message=f"暂不支持 {suffix or '无扩展名'} 文件，当前支持：{supported}",
    )