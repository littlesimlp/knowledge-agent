"""知识条目接口测试。"""

import uuid
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID, KnowledgeEntry
from app.models.knowledge_source import KnowledgeEntrySource, KnowledgeSource


async def test_create_entry(client: AsyncClient) -> None:
    response = await client.post(
        "/api/entries",
        json={
            "title": "测试标题",
            "content": "测试正文内容",
            "category": "测试",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "测试标题"
    assert body["category"] == "测试"
    # 断言是合法 UUID，而不是硬编码某个值
    assert uuid.UUID(body["id"])
    # 服务端自动填了 workspace_id
    assert body["workspace_id"] == str(DEFAULT_WORKSPACE_ID)
    # 数据库端生成的时间戳必须有值
    assert body["created_at"]
    assert body["updated_at"]


async def test_list_returns_created_entry(client: AsyncClient) -> None:
    await client.post(
        "/api/entries",
        json={"title": "列表测试", "content": "内容"},
    )

    response = await client.get("/api/entries")

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert "列表测试" in titles


async def test_get_missing_entry_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/entries/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_patch_only_updates_given_fields(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/entries",
            json={
                "title": "原标题",
                "content": "原正文",
                "summary": "原摘要",
                "category": "原分类",
            },
        )
    ).json()

    response = await client.patch(
        f"/api/entries/{created['id']}",
        json={"category": "新分类"},
    )

    assert response.status_code == 200
    body = response.json()
    # 只有 category 变了，其它字段必须原样保留
    assert body["category"] == "新分类"
    assert body["title"] == "原标题"
    assert body["content"] == "原正文"
    assert body["summary"] == "原摘要"


async def test_delete_entry(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/entries",
            json={"title": "待删除", "content": "内容"},
        )
    ).json()

    delete_response = await client.delete(f"/api/entries/{created['id']}")
    assert delete_response.status_code == 204

    # 删完再查应该 404
    assert (await client.get(f"/api/entries/{created['id']}")).status_code == 404


async def test_tests_are_isolated(client: AsyncClient) -> None:
    """这个测试依赖上一条测试什么都没留下。

    如果事务回滚失效，前面几个测试创建的数据会泄漏到这里。
    """
    response = await client.get("/api/entries")
    assert response.json() == []

async def test_delete_entry_removes_orphan_source_and_file(
    client: AsyncClient,
    session: AsyncSession,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """删条目后，来源记录和磁盘文件都应消失（D-020）。"""
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    created = (
        await client.post(
            "/api/imports/file",
            files={"file": ("note.md", b"# title\n\nbody content", "text/markdown")},
            data={"title": "要被删除的条目"},
        )
    ).json()

    uploads = tmp_path / "uploads"
    assert len(list(uploads.iterdir())) == 1

    response = await client.delete(f"/api/entries/{created['entry']['id']}")

    assert response.status_code == 204
    # 来源记录没了
    assert (await session.execute(select(KnowledgeSource))).scalars().all() == []
    # 磁盘文件也没了
    assert list(uploads.iterdir()) == []


async def test_shared_source_is_not_deleted(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """两个条目共享一个来源时，删其中一个不能删掉来源。"""
    source = KnowledgeSource(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="pasted_text",
        source_name="共享来源",
        extracted_text="same text",
    )
    entry_a = KnowledgeEntry(
        workspace_id=DEFAULT_WORKSPACE_ID, title="条目 A", content="a"
    )
    entry_b = KnowledgeEntry(
        workspace_id=DEFAULT_WORKSPACE_ID, title="条目 B", content="b"
    )
    session.add_all([source, entry_a, entry_b])
    await session.flush()
    session.add_all(
        [
            KnowledgeEntrySource(entry_id=entry_a.id, source_id=source.id),
            KnowledgeEntrySource(entry_id=entry_b.id, source_id=source.id),
        ]
    )
    await session.commit()

    response = await client.delete(f"/api/entries/{entry_a.id}")

    assert response.status_code == 204
    # B 还引用着它，来源必须保留
    remaining = (await session.execute(select(KnowledgeSource))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == source.id


async def test_delete_pasted_source_does_not_touch_files(
    client: AsyncClient,
    session: AsyncSession,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """粘贴文本类型的来源没有 file_path，删除时不能去动磁盘。"""
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    created = (
        await client.post(
            "/api/imports/text",
            json={"text": "一段粘贴的文本", "title": "粘贴的条目"},
        )
    ).json()

    response = await client.delete(f"/api/entries/{created['entry']['id']}")

    assert response.status_code == 204
    assert (await session.execute(select(KnowledgeSource))).scalars().all() == []
    # 从未上传过文件，uploads 目录不该被创建
    assert not (tmp_path / "uploads").exists()