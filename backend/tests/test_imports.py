"""导入接口测试。"""

from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge_source import KnowledgeEntrySource, KnowledgeSource


# --------------------------------------------------------------------------
# 粘贴文本（M2-3）
# --------------------------------------------------------------------------
async def test_import_text_creates_entry_and_source(client: AsyncClient) -> None:
    response = await client.post(
        "/api/imports/text",
        json={
            "text": "这是原始笔记的完整内容",
            "title": "我的第一条导入",
            "category": "笔记",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()

    assert body["entry"]["title"] == "我的第一条导入"
    # 没传 content 时应回退为原文
    assert body["entry"]["content"] == "这是原始笔记的完整内容"
    assert body["entry"]["category"] == "笔记"

    assert body["source"]["source_type"] == "pasted_text"
    assert body["source"]["source_excerpt"] == "这是原始笔记的完整内容"


async def test_import_keeps_original_text_in_source(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """原文必须完整存进来源表，不能被 content 覆盖。"""
    await client.post(
        "/api/imports/text",
        json={
            "text": "很长的原文" * 100,
            "title": "标题",
            "content": "我只想保存这一句精炼版",
        },
    )

    source = (await session.execute(select(KnowledgeSource))).scalars().one()
    assert source.extracted_text == "很长的原文" * 100
    # 展示片段被截断到 200 字符
    assert len(source.source_excerpt or "") == 200


async def test_import_creates_link_row(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """关联表必须真的写了一行，否则条目和来源就是断开的。"""
    await client.post(
        "/api/imports/text",
        json={"text": "内容", "title": "标题"},
    )

    links = (await session.execute(select(KnowledgeEntrySource))).scalars().all()
    assert len(links) == 1
    assert links[0].entry_id is not None
    assert links[0].source_id is not None


async def test_import_content_overrides_text(client: AsyncClient) -> None:
    response = await client.post(
        "/api/imports/text",
        json={
            "text": "原始全文",
            "title": "标题",
            "content": "用户精炼后的正文",
        },
    )

    assert response.status_code == 201
    assert response.json()["entry"]["content"] == "用户精炼后的正文"


async def test_import_blank_text_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/imports/text",
        json={"text": "   \n\t  ", "title": "标题"},
    )

    assert response.status_code == 422


async def test_imported_entry_is_listed(client: AsyncClient) -> None:
    await client.post(
        "/api/imports/text",
        json={"text": "内容", "title": "导入后应出现在列表里"},
    )

    listed = await client.get("/api/entries")
    titles = [item["title"] for item in listed.json()]
    assert "导入后应出现在列表里" in titles


# --------------------------------------------------------------------------
# 文件上传（M2-4）
# --------------------------------------------------------------------------
async def test_import_markdown_file(
    client: AsyncClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    files = {"file": ("note.md", "# 标题\n\n正文内容".encode(), "text/markdown")}
    data = {"title": "上传的笔记", "category": "测试"}

    response = await client.post("/api/imports/file", files=files, data=data)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["entry"]["title"] == "上传的笔记"
    assert body["entry"]["content"].startswith("# 标题")
    assert body["source"]["source_type"] == "file"
    assert body["source"]["source_name"] == "note.md"
    # 存的是相对路径，不是绝对路径
    assert body["source"]["file_path"].startswith("uploads/")
    assert not body["source"]["file_path"].startswith("/")

    # 文件真的落在磁盘上，且文件名不是用户提供的
    saved = list((tmp_path / "uploads").iterdir())
    assert len(saved) == 1
    assert saved[0].suffix == ".md"
    assert saved[0].name != "note.md"


async def test_import_file_title_defaults_to_stem(
    client: AsyncClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    files = {"file": ("我的笔记.md", "内容".encode(), "text/markdown")}

    response = await client.post("/api/imports/file", files=files)

    assert response.status_code == 201
    assert response.json()["entry"]["title"] == "我的笔记"


async def test_import_unsupported_file_type(
    client: AsyncClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    files = {"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")}

    response = await client.post("/api/imports/file", files=files)

    assert response.status_code == 415


async def test_import_oversized_file_rejected(
    client: AsyncClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    files = {"file": ("big.md", ("x" * 50).encode(), "text/markdown")}

    response = await client.post("/api/imports/file", files=files)

    assert response.status_code == 413
    # 超限时不应该落盘
    assert not (tmp_path / "uploads").exists()


async def test_import_empty_file_leaves_no_garbage(
    client: AsyncClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    files = {"file": ("empty.md", b"   \n\t ", "text/markdown")}

    response = await client.post("/api/imports/file", files=files)

    assert response.status_code == 422
    # 解析失败后，刚落的盘必须被删掉
    uploads = tmp_path / "uploads"
    assert not uploads.exists() or not list(uploads.iterdir())