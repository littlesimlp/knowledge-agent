"""解析器测试。"""

from pathlib import Path

from app.parsers import parse_file
from app.parsers.base import ParseStatus


def _write(tmp_path: Path, name: str, content: str, encoding: str = "utf-8") -> Path:
    path = tmp_path / name
    # newline="" 关掉平台的换行符转译。
    # 默认值 None 会在 Windows 上把 "\n" 变成 "\r\n"，
    # 于是传入 "\r\n" 会写出 "\r\r\n" —— 测试的输入就不是你以为的那个了。
    path.write_text(content, encoding=encoding, newline="")
    return path


def test_markdown_ok(tmp_path: Path) -> None:
    path = _write(tmp_path, "note.md", "# 标题\n\n正文内容")
    result = parse_file(path)
    assert result.status is ParseStatus.OK
    assert result.ok is True
    assert result.text.startswith("# 标题")
    assert "正文内容" in result.text


def test_plain_text_ok(tmp_path: Path) -> None:
    path = _write(tmp_path, "note.txt", "第一行\n第二行")
    result = parse_file(path)
    assert result.status is ParseStatus.OK
    assert result.text == "第一行\n第二行"


def test_gb18030_encoding(tmp_path: Path) -> None:
    """Windows 下用记事本存的 GBK/GB18030 文件必须能读。"""
    path = _write(tmp_path, "gbk.txt", "中文内容测试", encoding="gb18030")
    result = parse_file(path)
    assert result.status is ParseStatus.OK
    assert result.text == "中文内容测试"


def test_utf8_bom_stripped(tmp_path: Path) -> None:
    path = _write(tmp_path, "bom.md", "\ufeff# 带BOM的标题")
    result = parse_file(path)
    assert result.status is ParseStatus.OK
    # BOM 必须被吃掉，否则第一条 Markdown 标题解析不出来
    assert result.text == "# 带BOM的标题"


def test_crlf_normalized(tmp_path: Path) -> None:
    path = _write(tmp_path, "crlf.txt", "行一\r\n行二\r\n行三")
    result = parse_file(path)
    assert result.status is ParseStatus.OK
    assert "\r" not in result.text
    assert result.text == "行一\n行二\n行三"


def test_empty_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "empty.txt", "")
    result = parse_file(path)
    assert result.status is ParseStatus.EMPTY
    assert result.ok is False
    assert result.message


def test_whitespace_only(tmp_path: Path) -> None:
    path = _write(tmp_path, "blank.txt", "   \n\n\t  \n")
    result = parse_file(path)
    assert result.status is ParseStatus.EMPTY


def test_unsupported_suffix(tmp_path: Path) -> None:
    path = _write(tmp_path, "doc.docx", "whatever")
    result = parse_file(path)
    assert result.status is ParseStatus.UNSUPPORTED


def test_pdf_is_unsupported_for_now(tmp_path: Path) -> None:
    """PDF 支持在 M2-5，此测试固定当前行为，M2-5 时必须改写它。"""
    path = _write(tmp_path, "doc.pdf", "%PDF-1.4 fake")
    result = parse_file(path)
    assert result.status is ParseStatus.UNSUPPORTED
    assert ".pdf" in result.message


def test_missing_file(tmp_path: Path) -> None:
    result = parse_file(tmp_path / "nope.txt")
    assert result.status is ParseStatus.FAILED
    assert result.message