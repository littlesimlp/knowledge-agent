"""纯文本与 Markdown 解析。

编码策略：先按 UTF-8（含 BOM）解码，失败再试 GB18030（Windows 中文环境常见）。
不吞错误、不返回乱码——解不出来就明确告诉用户。
"""

from pathlib import Path

from app.parsers.base import ParseResult, ParseStatus

TEXT_SUFFIXES = frozenset({".txt", ".md", ".markdown"})

# 顺序有讲究：utf-8-sig 会顺带吃掉 BOM，gb18030 是中文环境的兜底
_ENCODINGS = ("utf-8-sig", "gb18030")


def _normalize(text: str) -> str:
    """统一换行符为 LF，避免 Windows CRLF 影响后续的行匹配与分页处理。"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_text(path: Path) -> ParseResult:
    """解析 .txt / .md / .markdown 文件。"""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return ParseResult(
            status=ParseStatus.FAILED,
            message=f"读取文件失败：{exc}",
        )

    for encoding in _ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue

        text = _normalize(text).strip()
        if not text:
            return ParseResult(
                status=ParseStatus.EMPTY,
                message="文件内容为空，没有可提取的文字",
            )
        return ParseResult(status=ParseStatus.OK, text=text)

    return ParseResult(
        status=ParseStatus.FAILED,
        message="无法识别文件编码（已尝试 UTF-8 / GB18030），可能不是纯文本文件",
    )