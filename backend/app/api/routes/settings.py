"""LLM 设置接口。

没有鉴权：服务只绑 127.0.0.1，本机进程本来就能读全库。
如果将来开放到局域网，必须先加认证再暴露这些接口。
"""

from fastapi import APIRouter, Response, status

from app.api.deps import LLMDep, llm_unavailable
from app.schemas.settings import LLMSettingsRead, LLMSettingsUpdate, LLMTestResult
from app.services.llm.base import LLMError
from app.services.llm_config import (
    clear_llm_config,
    load_llm_config,
    mask_key,
    save_llm_config,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_read() -> LLMSettingsRead:
    config = load_llm_config()
    return LLMSettingsRead(
        provider=config.provider,
        base_url=config.base_url,
        model=config.model,
        api_key_configured=bool(config.api_key),
        api_key_hint=mask_key(config.api_key),
    )


@router.get("/llm", response_model=LLMSettingsRead, summary="读取当前 LLM 配置")
async def read_llm_settings() -> LLMSettingsRead:
    return _to_read()


@router.put("/llm", response_model=LLMSettingsRead, summary="保存 LLM 配置")
async def update_llm_settings(payload: LLMSettingsUpdate) -> LLMSettingsRead:
    save_llm_config(
        provider=payload.provider,
        base_url=payload.base_url,
        model=payload.model,
        api_key="" if payload.clear_api_key else payload.api_key,
    )
    return _to_read()


@router.delete("/llm", status_code=status.HTTP_204_NO_CONTENT, summary="恢复 .env 配置")
async def reset_llm_settings() -> Response:
    clear_llm_config()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/llm/test", response_model=LLMTestResult, summary="测试模型连接")
async def test_llm_settings(llm: LLMDep) -> LLMTestResult:
    try:
        await llm.suggest_entry("连接测试：这是一段示例文本。")
    except LLMError as exc:
        raise llm_unavailable(exc) from exc
    return LLMTestResult(ok=True, provider=llm.name)