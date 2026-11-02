"""来源接口测试。

两条关键约定：
1. 条目来源列表**不返回** extracted_text（避免响应体被全文撑爆）
2. 全文只通过 `GET /api/sources/{id}` 获取，且跨空间一律 404
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_source import KnowledgeSource

ORIGINAL_TEXT = "这是需要完整保留的原文。" * 20


async def _import_text(client: AsyncClient, title: str = "来源测试") -> dict:
    """走真实导入接口，保证条目、来源、关联都由生产代码创建。"""
    response = await client.post(
        "/api/imports/text",
        json={"text": ORIGINAL_TEXT, "title": title},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_list_entry_sources_returns_metadata_without_text(
    client: AsyncClient,
) -> None:
    imported = await _import_text(client)

    response = await client.get(f"/api/entries/{imported['entry']['id']}/sources")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == imported["source"]["id"]
    assert body[0]["source_name"] == imported["source"]["source_name"]
    # 全文绝不能出现在列表响应里
    assert "extracted_text" not in body[0]


async def test_list_sources_of_missing_entry_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/entries/{uuid.uuid4()}/sources")
    assert response.status_code == 404


async def test_list_returns_only_linked_sources(client: AsyncClient) -> None:
    first = await _import_text(client, "第一条")
    second = await _import_text(client, "第二条")

    response = await client.get(f"/api/entries/{first['entry']['id']}/sources")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [first["source"]["id"]]
    assert second["source"]["id"] not in ids


async def test_get_source_returns_full_text(client: AsyncClient) -> None:
    imported = await _import_text(client)

    response = await client.get(f"/api/sources/{imported['source']['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["extracted_text"] == ORIGINAL_TEXT
    assert body["source_name"] == imported["source"]["source_name"]


async def test_get_missing_source_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/sources/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_source_in_other_workspace_returns_404(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """跨空间必须返回 404，不能因为知道 id 就读到别人的原文。"""
    foreign = KnowledgeSource(
        workspace_id=uuid.uuid4(),
        source_type="pasted_text",
        source_name="别人的来源",
        extracted_text="别人的私密原文",
    )
    session.add(foreign)
    await session.commit()

    response = await client.get(f"/api/sources/{foreign.id}")

    assert response.status_code == 404
