"""导入接口测试。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_source import KnowledgeEntrySource, KnowledgeSource


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