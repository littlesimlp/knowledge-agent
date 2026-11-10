"""LLM 设置接口测试。"""

import json

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """每个测试用独立 data 目录，且不读真实 .env 的 key。"""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_provider", "fake")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")


async def test_get_defaults_to_env(client: AsyncClient) -> None:
    response = await client.get("/api/settings/llm")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "fake"
    assert body["api_key_configured"] is False
    assert body["api_key_hint"] is None


async def test_put_saves_key_and_masks_it(client: AsyncClient) -> None:
    response = await client.put(
        "/api/settings/llm",
        json={
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "api_key": "sk-test-1234",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "deepseek"
    assert body["api_key_configured"] is True
    assert body["api_key_hint"] == "…1234"
    # 明文 key 绝不能出现在响应里
    assert "sk-test-1234" not in response.text

    saved = json.loads((settings.data_dir / "llm.json").read_text(encoding="utf-8"))
    assert saved["api_key"] == "sk-test-1234"


async def test_put_without_key_keeps_existing(client: AsyncClient) -> None:
    await client.put(
        "/api/settings/llm",
        json={
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "sk-keep-5678",
        },
    )

    response = await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "deepseek-chat"},
    )

    assert response.status_code == 200
    assert response.json()["api_key_hint"] == "…5678"


async def test_blank_api_key_keeps_existing(client: AsyncClient) -> None:
    await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "m", "api_key": "sk-keep-9999"},
    )

    response = await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "m", "api_key": "   "},
    )

    assert response.json()["api_key_hint"] == "…9999"


async def test_clear_api_key(client: AsyncClient) -> None:
    await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "m", "api_key": "sk-clear-1111"},
    )

    response = await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "m", "clear_api_key": True},
    )

    body = response.json()
    assert body["api_key_configured"] is False
    assert body["api_key_hint"] is None


async def test_delete_resets_to_env(client: AsyncClient) -> None:
    await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "m", "api_key": "sk-del-2222"},
    )

    assert (await client.delete("/api/settings/llm")).status_code == 204

    body = (await client.get("/api/settings/llm")).json()
    assert body["provider"] == "fake"
    assert body["api_key_configured"] is False


async def test_invalid_provider_returns_422(client: AsyncClient) -> None:
    response = await client.put(
        "/api/settings/llm",
        json={"provider": "openai", "model": "gpt", "api_key": "x"},
    )
    assert response.status_code == 422


async def test_real_provider_requires_model(client: AsyncClient) -> None:
    response = await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "", "api_key": "x"},
    )
    assert response.status_code == 422


async def test_key_and_clear_together_returns_422(client: AsyncClient) -> None:
    response = await client.put(
        "/api/settings/llm",
        json={
            "provider": "fake",
            "api_key": "x",
            "clear_api_key": True,
        },
    )
    assert response.status_code == 422


async def test_test_endpoint_with_fake(client: AsyncClient) -> None:
    response = await client.post("/api/settings/llm/test")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "provider": "fake"}


async def test_test_endpoint_without_key_returns_503(client: AsyncClient) -> None:
    await client.put(
        "/api/settings/llm",
        json={"provider": "deepseek", "model": "deepseek-chat"},
    )

    response = await client.post("/api/settings/llm/test")

    assert response.status_code == 503
    assert "AI 暂时不可用" in response.json()["detail"]