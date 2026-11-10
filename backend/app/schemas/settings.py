"""LLM 设置接口契约。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ProviderName = Literal["fake", "deepseek", "siliconflow"]


class LLMSettingsRead(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key_configured: bool
    api_key_hint: str | None


class LLMSettingsUpdate(BaseModel):
    provider: ProviderName
    base_url: str = Field(default="", max_length=2048)
    model: str = Field(default="", max_length=200)
    api_key: str | None = Field(default=None, max_length=2048)
    clear_api_key: bool = False

    @field_validator("api_key")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _check(self) -> "LLMSettingsUpdate":
        if self.provider != "fake" and not self.model.strip():
            raise ValueError("真实模型必须填写 model")
        if self.clear_api_key and self.api_key is not None:
            raise ValueError("api_key 与 clear_api_key 不能同时使用")
        return self


class LLMTestResult(BaseModel):
    ok: bool
    provider: str