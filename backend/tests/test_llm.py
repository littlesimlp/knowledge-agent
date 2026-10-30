"""LLM 适配层测试。

全部不联网：解析逻辑是纯函数，provider 用 FakeProvider。
"""

import pytest

from app.services.llm.base import EntrySuggestion, LLMError
from app.services.llm.fake import FakeProvider
from app.services.llm.openai_compat import parse_suggestion


def test_parse_clean_json() -> None:
    raw = '{"title":"标题","summary":"摘要","keywords":["a","b"],"category":"分类"}'

    result = parse_suggestion(raw)

    assert result.title == "标题"
    assert result.summary == "摘要"
    assert result.keywords == ("a", "b")
    assert result.category == "分类"
    assert result.is_empty() is False


def test_parse_json_in_code_fence() -> None:
    """模型经常把 JSON 包在 ```json 代码块里。"""
    raw = '```json\n{"title":"标题"}\n```'

    result = parse_suggestion(raw)

    assert result.title == "标题"


def test_parse_json_with_explanation_around_it() -> None:
    """模型有时会先解释一句再给 JSON。"""
    raw = '好的，整理结果如下：\n{"title":"标题","category":"分类"}\n希望有帮助。'

    result = parse_suggestion(raw)

    assert result.title == "标题"
    assert result.category == "分类"


def test_parse_missing_fields() -> None:
    result = parse_suggestion('{"title":"只有标题"}')

    assert result.title == "只有标题"
    assert result.summary is None
    assert result.keywords == ()
    assert result.category is None


def test_parse_wrong_types_are_dropped() -> None:
    """字段类型不对时丢弃该字段，而不是整体失败。"""
    raw = '{"title": 123, "summary": null, "keywords": "not-an-array", "category": ["x"]}'

    result = parse_suggestion(raw)

    assert result.title is None
    assert result.summary is None
    assert result.keywords == ()
    assert result.category is None
    assert result.is_empty() is True


def test_parse_truncates_too_long_title() -> None:
    """标题超过数据库上限时要截断，否则后续保存会失败。"""
    raw = '{"title": "' + "长" * 300 + '"}'

    result = parse_suggestion(raw)

    assert result.title is not None
    assert len(result.title) == 200


def test_parse_limits_keyword_count() -> None:
    raw = '{"keywords": ["k1","k2","k3","k4","k5","k6","k7","k8","k9","k10"]}'

    result = parse_suggestion(raw)

    assert len(result.keywords) == 8


def test_parse_empty_content_raises() -> None:
    with pytest.raises(LLMError):
        parse_suggestion("   ")


def test_parse_no_json_raises() -> None:
    with pytest.raises(LLMError):
        parse_suggestion("抱歉，我无法完成这个任务。")


def test_parse_broken_json_raises() -> None:
    with pytest.raises(LLMError):
        parse_suggestion('{"title": "缺少右括号"')


async def test_fake_provider_returns_suggestion() -> None:
    provider = FakeProvider(EntrySuggestion(title="固定标题"))

    result = await provider.suggest_entry("任意文本")

    assert result.title == "固定标题"


async def test_fake_provider_can_raise() -> None:
    provider = FakeProvider(error=LLMError("模拟超时"))

    with pytest.raises(LLMError, match="模拟超时"):
        await provider.suggest_entry("任意文本")