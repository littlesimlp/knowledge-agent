"""问答接口测试（M4-2）。

覆盖：无结果不调模型、合法引用映射、越界/空引用降级、模型失败 503、参数校验。
"""

import pytest
from httpx import AsyncClient

from app.main import app
from app.services.ask import NO_RESULTS_ANSWER, UNGROUNDED_ANSWER
from app.services.llm import get_llm_provider
from app.services.llm.base import AnswerDraft, LLMError
from app.services.llm.fake import FakeProvider
from app.services.llm.openai_compat import parse_answer


def _use_provider(monkeypatch: pytest.MonkeyPatch, provider: FakeProvider) -> None:
    monkeypatch.setitem(app.dependency_overrides, get_llm_provider, lambda: provider)


async def _create(client: AsyncClient, title: str, content: str) -> dict:
    response = await client.post(
        "/api/entries", json={"title": title, "content": content}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_no_results_does_not_call_model(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """检索为空时不能调用模型——用"会抛错"的 provider 证明它没被调用。"""
    _use_provider(monkeypatch, FakeProvider(error=LLMError("不应被调用")))

    response = await client.post("/api/ask", json={"question": "完全不存在的词"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reason"] == "no_results"
    assert body["grounded"] is False
    assert body["answer"] == NO_RESULTS_ANSWER
    assert body["citations"] == []


async def test_grounded_answer_maps_citation(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = await _create(
        client,
        "Docker 数据卷",
        "Docker 数据卷的区别：命名卷由 Docker 管理。",
    )
    _use_provider(
        monkeypatch,
        FakeProvider(answer=AnswerDraft("命名卷由 Docker 管理。", (1,))),
    )

    response = await client.post("/api/ask", json={"question": "Docker 数据卷"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["grounded"] is True
    assert body["reason"] == "ok"
    assert body["provider"] == "fake"
    assert body["answer"] == "命名卷由 Docker 管理。"
    assert len(body["citations"]) == 1
    assert body["citations"][0]["entry_id"] == entry["id"]
    assert body["citations"][0]["title"] == "Docker 数据卷"
    assert "Docker 数据卷" in body["citations"][0]["snippet"]


async def test_out_of_range_citation_degrades(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create(client, "Docker 数据卷", "Docker 数据卷的区别。")
    _use_provider(monkeypatch, FakeProvider(answer=AnswerDraft("答案", (99,))))

    response = await client.post("/api/ask", json={"question": "Docker 数据卷"})

    body = response.json()
    assert response.status_code == 200
    assert body["grounded"] is False
    assert body["reason"] == "ungrounded"
    assert body["answer"] == UNGROUNDED_ANSWER
    assert body["citations"] == []


async def test_empty_citations_degrades(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create(client, "Docker 数据卷", "Docker 数据卷的区别。")
    _use_provider(monkeypatch, FakeProvider(answer=AnswerDraft("没有引用的答案")))

    response = await client.post("/api/ask", json={"question": "Docker 数据卷"})

    body = response.json()
    assert body["grounded"] is False
    assert body["reason"] == "ungrounded"
    assert body["citations"] == []


async def test_duplicate_citations_are_deduped(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = await _create(client, "Docker 数据卷", "Docker 数据卷的区别。")
    _use_provider(monkeypatch, FakeProvider(answer=AnswerDraft("答案", (1, 1))))

    response = await client.post("/api/ask", json={"question": "Docker 数据卷"})

    body = response.json()
    assert body["grounded"] is True
    assert len(body["citations"]) == 1
    assert body["citations"][0]["entry_id"] == entry["id"]


async def test_model_failure_returns_503(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create(client, "Docker 数据卷", "Docker 数据卷的区别。")
    _use_provider(monkeypatch, FakeProvider(error=LLMError("模型调用超时")))

    response = await client.post("/api/ask", json={"question": "Docker 数据卷"})

    assert response.status_code == 503
    assert "AI 暂时不可用" in response.json()["detail"]
    assert "超时" in response.json()["detail"]


async def test_blank_question_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 422


async def test_limit_out_of_range_returns_422(client: AsyncClient) -> None:
    for invalid in (0, 11):
        response = await client.post(
            "/api/ask",
            json={"question": "任意问题", "limit": invalid},
        )
        assert response.status_code == 422


def test_parse_answer_clean_json() -> None:
    draft = parse_answer('{"answer": "回答", "citations": [1, 2]}')

    assert draft.answer == "回答"
    assert draft.citation_numbers == (1, 2)


def test_parse_answer_normalizes_strings_and_dedupes() -> None:
    draft = parse_answer('{"answer": "回答", "citations": ["1", 1, 2, true, 0]}')

    assert draft.citation_numbers == (1, 2, 0)


def test_parse_answer_missing_answer_raises() -> None:
    with pytest.raises(LLMError):
        parse_answer('{"citations": [1]}')