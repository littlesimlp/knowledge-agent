"""PDF 解析器测试。

测试用 PDF 全部由 PyMuPDF 现场生成：可复现，且不含任何真实文档内容。
"""

from pathlib import Path

import pymupdf

from app.parsers import parse_file
from app.parsers.base import ParseStatus


def _make_pdf(path: Path, *, with_text: bool, pages: int = 2) -> Path:
    """生成测试 PDF。with_text=False 时只有矢量图形，没有文字层。"""
    doc = pymupdf.open()
    for index in range(1, pages + 1):
        page = doc.new_page()
        if with_text:
            # 每页写多行：真实文档每页有数百字符。
            # 只写一两行会被 D-018 的「平均每页 < 25 字符」阈值误判为扫描件，
            # 那是夹具不真实，不是阈值有问题。
            for line in range(1, 9):
                page.insert_text(
                    (72, 72 + line * 18),
                    f"Page {index} line {line} content marker",
                )
        else:
            page.draw_rect(pymupdf.Rect(72, 72, 400, 400))
    doc.save(path)
    doc.close()
    return path


def test_pdf_with_text_is_ok(tmp_path: Path) -> None:
    path = _make_pdf(tmp_path / "with_text.pdf", with_text=True, pages=2)

    result = parse_file(path)

    assert result.status is ParseStatus.OK
    assert result.page_count == 2
    assert "Page 1 line 1 content marker" in result.text
    assert "Page 2 line 8 content marker" in result.text
    # M2-6 的噪音过滤依赖页级文本
    assert len(result.pages) == 2


def test_pdf_without_text_layer_is_empty(tmp_path: Path) -> None:
    """只有图形的 PDF 等价于扫描件：能打开，但提取不到文字。"""
    path = _make_pdf(tmp_path / "image_only.pdf", with_text=False, pages=3)

    result = parse_file(path)

    assert result.status is ParseStatus.EMPTY
    assert result.page_count == 3
    assert "OCR" in result.message or "扫描" in result.message


def test_corrupted_pdf_fails(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.4 this is not a real pdf")

    result = parse_file(path)

    assert result.status is ParseStatus.FAILED
    assert result.message


def test_parse_file_dispatches_pdf(tmp_path: Path) -> None:
    path = _make_pdf(tmp_path / "dispatch.pdf", with_text=True, pages=1)

    result = parse_file(path)

    assert result.status is ParseStatus.OK

def _make_pdf_with_noise(path: Path, *, pages: int = 3) -> Path:
    """生成带页眉和页码的 PDF，用来验证噪音过滤。

    注意：页眉和页码要放在不同的 y 坐标，
    否则 PyMuPDF 会把它们合并成同一行文字。
    """
    doc = pymupdf.open()
    for index in range(1, pages + 1):
        page = doc.new_page()
        page.insert_text((72, 60), "RUNNING HEADER OF THE DOCUMENT")   # 页眉
        page.insert_text((300, 780), str(index))                       # 页码（页脚位置）
        for line in range(1, 6):
            page.insert_text(
                (72, 118 + line * 18),
                f"body content of page {index} line {line}",
            )
    doc.save(path)
    doc.close()
    return path


def test_pdf_noise_is_filtered(tmp_path: Path) -> None:
    """页眉和页码必须被去掉，正文必须完整保留。"""
    path = _make_pdf_with_noise(tmp_path / "noisy.pdf", pages=3)

    result = parse_file(path)

    assert result.status is ParseStatus.OK
    assert "RUNNING HEADER OF THE DOCUMENT" not in result.text
    assert "body content of page 1 line 1" in result.text
    assert "body content of page 3 line 5" in result.text