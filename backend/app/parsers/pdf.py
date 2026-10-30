"""PDF 解析（PyMuPDF）。

- D-017：选 PyMuPDF 而非 pypdf，文本提取质量显著更好
- D-018：平均每页字符数 < 25 判定为"没有文字层"（扫描件），返回 EMPTY 而非 FAILED
"""

from pathlib import Path

import pymupdf

from app.parsers.base import ParseResult, ParseStatus
from app.parsers.cleanup import clean_pages

PDF_SUFFIXES = frozenset({".pdf"})

MIN_CHARS_PER_PAGE = 25


def parse_pdf(path: Path) -> ParseResult:
    """解析 PDF，返回逐页文本与整体状态。"""
    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # pymupdf 的异常类型不稳定，宽泛捕获
        return ParseResult(
            status=ParseStatus.FAILED,
            message=f"无法打开 PDF（文件可能损坏）：{exc}",
        )

    try:
        if doc.needs_pass:
            return ParseResult(
                status=ParseStatus.FAILED,
                message="这个 PDF 有密码保护，无法提取内容",
            )

        page_count = doc.page_count
        if page_count == 0:
            return ParseResult(status=ParseStatus.EMPTY, message="PDF 里没有任何页面")

        pages = tuple(page.get_text() for page in doc)
    finally:
        doc.close()

    # D-016：先去掉页眉/页脚/页码，再做"是否为扫描件"的判定
    pages = clean_pages(pages)

    total_chars = sum(len(p.strip()) for p in pages)

    total_chars = sum(len(p.strip()) for p in pages)
    chars_per_page = total_chars / page_count

    if chars_per_page < MIN_CHARS_PER_PAGE:
        return ParseResult(
            status=ParseStatus.EMPTY,
            message=(
                f"这份 PDF 似乎没有文字层（平均每页 {chars_per_page:.0f} 个字符），"
                "可能是扫描件。当前版本不支持 OCR，无法提取内容。"
            ),
            page_count=page_count,
            pages=pages,
        )

    text = "\n".join(p.strip() for p in pages if p.strip()).strip()
    return ParseResult(
        status=ParseStatus.OK,
        text=text,
        page_count=page_count,
        pages=pages,
    )