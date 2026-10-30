"""建议接口测试。

用 app.dependency_overrides 注入 FakeProvider —— 不联网、不依赖真实 key。
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID, KnowledgeEntry
from app.services.llm import get_llm_provider
from app.services.llm.base import EntrySuggestion, LLMError
from app.services.llm.fake import FakeProvider


def _use_provider(monkeypatch: pytest.MonkeyPatch, provider: FakeProvider) -> None:
    """临时替换 provider；monkeypatch 会在测试结束后自动还原。"""
    monkeypatch.setitem(app.dependency_overrides, get_llm_provider, lambda: provider)


async def test_suggestion_returns_model_output(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_provider(
        monkeypatch,
        FakeProvider(
            EntrySuggestion(
                title="Docker 挂载方式",
                summary="命名卷与绑定挂载的区别",
                keywords=("docker", "volume"),
                category="容器",
            )
        ),
    )

    response = await client.post(
        "/api/suggestions",
        json={"text": "一段关于 Docker 挂载方式的技术笔记"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Docker 挂载方式"
    assert body["summary"] == "命名卷与绑定挂载的区别"
    assert body["keywords"] == ["docker", "volume"]
    assert body["category"] == "容器"
    assert body["provider"] == "fake"


async def test_suggestion_does_not_persist_anything(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """建议接口绝不能落库——用户确认之后才算数。"""
    _use_provider(monkeypatch, FakeProvider())

    await client.post("/api/suggestions", json={"text": "随便一段文本"})

    listed = await client.get("/api/entries")
    assert listed.json() == []


async def test_suggestion_failure_returns_503(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI 不可用时返回 503，客户端应降级为手动填写。"""
    _use_provider(monkeypatch, FakeProvider(error=LLMError("模型调用超时")))

    response = await client.post("/api/suggestions", json={"text": "一段文本"})

    assert response.status_code == 503
    assert "AI 暂时不可用" in response.json()["detail"]
    assert "超时" in response.json()["detail"]


async def test_blank_text_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/suggestions", json={"text": "   \n\t "})

    assert response.status_code == 422


async def test_empty_suggestion_is_valid_response(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """模型什么都给不出来时，接口仍是 200，字段为空。"""
    _use_provider(monkeypatch, FakeProvider(EntrySuggestion()))

    response = await client.post("/api/suggestions", json={"text": "无意义内容"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] is None
    assert body["keywords"] == []

async def test_entry_suggestion_returns_advice(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """对已有条目求建议。"""
    created = (
        await client.post(
            "/api/entries",
            json={"title": "原标题", "content": "Docker 命名卷与绑定挂载的区别"},
        )
    ).json()
    _use_provider(
        monkeypatch,
        FakeProvider(EntrySuggestion(title="建议的新标题", category="容器")),
    )

    response = await client.post(f"/api/entries/{created['id']}/suggestions")

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "建议的新标题"
    assert response.json()["provider"] == "fake"


async def test_entry_suggestion_does_not_modify_entry(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """求建议绝不能改动条目本身——确认权在用户。"""
    created = (
        await client.post(
            "/api/entries",
            json={"title": "原标题", "content": "一些正文内容"},
        )
    ).json()
    _use_provider(monkeypatch, FakeProvider(EntrySuggestion(title="完全不同的标题")))

    await client.post(f"/api/entries/{created['id']}/suggestions")

    after = (await client.get(f"/api/entries/{created['id']}")).json()
    assert after["title"] == "原标题"


async def test_entry_suggestion_missing_entry_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.post(f"/api/entries/{uuid.uuid4()}/suggestions")

    assert response.status_code == 404


async def test_entry_suggestion_requires_content(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """正文为空白时直接拒绝，不必浪费一次模型调用。"""
    entry = KnowledgeEntry(
        workspace_id=DEFAULT_WORKSPACE_ID,
        title="空条目",
        content="   ",
    )
    session.add(entry)
    await session.commit()
    _use_provider(monkeypatch, FakeProvider())

    response = await client.post(f"/api/entries/{entry.id}/suggestions")

    assert response.status_code == 422
    assert "没有正文" in response.json()["detail"]


async def test_entry_suggestion_llm_failure_returns_503(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = (
        await client.post(
            "/api/entries",
            json={"title": "标题", "content": "正文"},
        )
    ).json()
    _use_provider(monkeypatch, FakeProvider(error=LLMError("连接被拒绝")))

    response = await client.post(f"/api/entries/{created['id']}/suggestions")

    assert response.status_code == 503
    assert "AI 暂时不可用" in response.json()["detail"]