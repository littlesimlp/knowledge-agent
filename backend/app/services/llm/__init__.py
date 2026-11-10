"""LLM 适配层的工厂。

业务层只需要 `get_llm_provider()`，不需要知道用的是哪家模型、key 从哪来。
配置来源：data/llm.json（前端可改）> .env。
"""

from app.services.llm.base import EntrySuggestion, LLMError, LLMProvider
from app.services.llm.fake import FakeProvider
from app.services.llm.openai_compat import OpenAICompatProvider
from app.services.llm_config import load_llm_config

__all__ = ["EntrySuggestion", "LLMError", "LLMProvider", "get_llm_provider"]

# 各平台默认地址；model 不设默认值，因为模型名会变，必须显式配置
_DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
}


def get_llm_provider() -> LLMProvider:
    config = load_llm_config()
    provider = config.provider

    if provider == "fake":
        return FakeProvider()

    if provider not in _DEFAULT_BASE_URLS:
        supported = "、".join(["fake", *_DEFAULT_BASE_URLS])
        raise LLMError(f"未知的 LLM_PROVIDER：{provider}，当前支持：{supported}")

    return OpenAICompatProvider(
        name=provider,
        base_url=config.base_url or _DEFAULT_BASE_URLS[provider],
        api_key=config.api_key,
        model=config.model,
        timeout_seconds=config.timeout_seconds,
        max_input_chars=config.max_input_chars,
    )