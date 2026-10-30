"""LLM 适配层的工厂。

业务层只需要 `get_llm_provider().suggest_entry(text)`，
不需要知道用的是哪家模型、走什么协议、key 从哪来。
"""

from app.core.config import settings
from app.services.llm.base import EntrySuggestion, LLMError, LLMProvider
from app.services.llm.fake import FakeProvider
from app.services.llm.openai_compat import OpenAICompatProvider

__all__ = ["EntrySuggestion", "LLMError", "LLMProvider", "get_llm_provider"]

# 各平台默认地址；model 不设默认值，因为模型名会变，必须显式配置
_DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
}


def get_llm_provider() -> LLMProvider:
    """按配置创建 provider。

    默认 llm_provider = "fake"，所以没配 key 时应用仍能正常启动和运行。
    """
    provider = settings.llm_provider.strip().lower()

    if provider == "fake":
        return FakeProvider()

    if provider not in _DEFAULT_BASE_URLS:
        supported = "、".join(["fake", *_DEFAULT_BASE_URLS])
        raise LLMError(f"未知的 LLM_PROVIDER：{provider}，当前支持：{supported}")

    return OpenAICompatProvider(
        name=provider,
        base_url=settings.llm_base_url or _DEFAULT_BASE_URLS[provider],
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_input_chars=settings.llm_max_input_chars,
    )