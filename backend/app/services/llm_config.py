"""LLM 运行时配置。

优先级：`data/llm.json` > 环境变量/.env。
前端保存的配置只覆盖这四个字段，其余（超时、输入上限）仍由 .env 决定。

安全约定：key 只写不读回；接口只返回后 4 位。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

CONFIG_FILENAME = "llm.json"
_OVERRIDE_KEYS = {"provider", "base_url", "model", "api_key"}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    model: str
    api_key: str
    timeout_seconds: float
    max_input_chars: int


def config_path() -> Path:
    return settings.data_dir / CONFIG_FILENAME


def _read_overrides() -> dict[str, str]:
    path = config_path()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # 文件坏了就回退 env，不让应用起不来
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        key: value.strip()
        for key, value in data.items()
        if key in _OVERRIDE_KEYS and isinstance(value, str)
    }


def load_llm_config() -> LLMConfig:
    overrides = _read_overrides()
    return LLMConfig(
        provider=overrides.get("provider", settings.llm_provider).strip().lower(),
        base_url=overrides.get("base_url", settings.llm_base_url).strip(),
        model=overrides.get("model", settings.llm_model).strip(),
        api_key=overrides.get("api_key", settings.llm_api_key).strip(),
        timeout_seconds=settings.llm_timeout_seconds,
        max_input_chars=settings.llm_max_input_chars,
    )


def save_llm_config(
    *,
    provider: str,
    base_url: str,
    model: str,
    api_key: str | None,
) -> LLMConfig:
    """写覆盖文件；api_key=None 表示保持原值，"" 表示清除。"""
    current = load_llm_config()
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "provider": provider.strip().lower(),
        "base_url": base_url.strip(),
        "model": model.strip(),
        "api_key": current.api_key if api_key is None else api_key.strip(),
    }

    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    temp.replace(path)

    return load_llm_config()


def clear_llm_config() -> None:
    config_path().unlink(missing_ok=True)


def mask_key(key: str) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "…"
    return f"…{key[-4:]}"