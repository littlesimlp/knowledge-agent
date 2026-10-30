"""噪音过滤的单元测试（全部用合成数据，不含任何真实文档内容）。"""

from app.parsers.cleanup import clean_pages, find_repeated_short_lines, is_page_number


def test_repeated_header_removed() -> None:
    pages = [f"RUNNING HEADER\nbody of page {i}" for i in range(1, 6)]

    cleaned = clean_pages(pages)

    assert all("RUNNING HEADER" not in p for p in cleaned)
    assert all(f"body of page {i}" in cleaned[i - 1] for i in range(1, 6))


def test_page_numbers_removed() -> None:
    pages = [f"{i}\nbody of page {i}" for i in range(1, 4)]

    cleaned = clean_pages(pages)

    assert all("1" != p.strip() for p in cleaned)
    assert all(f"body of page {i}" in cleaned[i - 1] for i in range(1, 4))


def test_line_on_minority_of_pages_is_kept() -> None:
    """只在 1/5 页出现的短行不能删——它可能是正文里的小标题。"""
    pages = ["UNIQUE SECTION TITLE\nbody 1"] + [f"body {i}" for i in range(2, 6)]

    cleaned = clean_pages(pages)

    assert "UNIQUE SECTION TITLE" in cleaned[0]


def test_single_page_skips_repeat_rule() -> None:
    """一页时无法判断重复，只应用页码规则。"""
    cleaned = clean_pages(["SOME TITLE\nbody text"])

    assert "SOME TITLE" in cleaned[0]


def test_long_repeated_line_is_kept() -> None:
    """重复但很长的行不删——可能是每页都有的免责声明/长标题。"""
    long_line = "x" * 100
    pages = [f"{long_line}\nbody {i}" for i in range(1, 4)]

    cleaned = clean_pages(pages)

    assert all(long_line in p for p in cleaned)


def test_blank_lines_preserved() -> None:
    cleaned = clean_pages(["line one\n\nline two"])

    assert "\n\n" in cleaned[0]


def test_is_page_number_cases() -> None:
    assert is_page_number("12")
    assert is_page_number("- 12 -")
    assert is_page_number("  7  ")
    assert not is_page_number("Chapter 12")
    assert not is_page_number("2024 年总结")
    assert not is_page_number("")


def test_find_repeated_short_lines() -> None:
    pages = ["HEADER\nbody 1", "HEADER\nbody 2", "HEADER\nbody 3"]

    assert find_repeated_short_lines(pages) == {"HEADER"}