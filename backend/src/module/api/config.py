import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from module.conf import settings
from module.core import AppContext
from module.models import APIResponse, Config
from module.parser.analyser.llm import LLMParser
from module.security.api import UNAUTHORIZED, get_current_user

from .deps import get_context

router = APIRouter(prefix="/config", tags=["config"])
logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = ("password", "api_key", "token", "secret")
_MASK = "********"


def _is_sensitive(key: str) -> bool:
    return any(s in key.lower() for s in _SENSITIVE_KEYS)


def _sanitize_dict(d: dict) -> dict:
    """Recursively mask string values whose keys contain sensitive keywords."""
    result: dict = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [
                _sanitize_dict(item) if isinstance(item, dict) else item for item in v
            ]
        elif isinstance(v, str) and _is_sensitive(k):
            result[k] = _MASK
        else:
            result[k] = v
    return result


def _restore_masked(incoming: dict, current: dict) -> dict:
    """Replace masked sentinel values with real values from current config."""
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(current.get(k), dict):
            _restore_masked(v, current[k])
        elif isinstance(v, list) and isinstance(current.get(k), list):
            cur_list = current[k]
            for i, item in enumerate(v):
                if (
                    isinstance(item, dict)
                    and i < len(cur_list)
                    and isinstance(cur_list[i], dict)
                ):
                    _restore_masked(item, cur_list[i])
        elif v == _MASK and _is_sensitive(k):
            incoming[k] = current.get(k, v)
    return incoming


@router.get("/get", dependencies=[Depends(get_current_user)])
async def get_config():
    """Return the current configuration with sensitive fields masked."""
    return _sanitize_dict(settings.dict())


@router.patch(
    "/update", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def update_config(config: Config, ctx: AppContext = Depends(get_context)):
    """Persist and reload configuration from the supplied payload."""
    try:
        config_dict = _restore_masked(config.dict(), settings.dict())
        # settings.save() does synchronous file I/O; keep it off the event loop.
        await asyncio.to_thread(settings.save, config_dict=config_dict)
        # reload_settings reloads from disk, resets the shared HTTP client,
        # rebuilds notifications, and re-applies the RSS/rename loops.
        await ctx.reload_settings()
        logger.info("Config updated")
        return JSONResponse(
            status_code=200,
            content={
                "msg_en": "Update config successfully.",
                "msg_zh": "更新配置成功。",
            },
        )
    except Exception as e:
        logger.warning(e)
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Update config failed.", "msg_zh": "更新配置失败。"},
        )


class LLMModelsRequest(BaseModel):
    provider: Literal["openai", "anthropic", "gemini"] = "openai"
    api_key: str = ""
    base_url: str = ""


class LLMModelsResponse(BaseModel):
    models: list[str]


@router.post(
    "/llm/models",
    response_model=LLMModelsResponse,
    dependencies=[Depends(get_current_user)],
)
async def list_llm_models(req: LLMModelsRequest):
    """拉取所选 LLM 提供商的可用模型列表。

    表单里的密钥若是掩码（用户未改动已保存的密钥），回退到已保存值。
    """
    api_key = req.api_key
    if not api_key or api_key == _MASK:
        api_key = settings.llm.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="LLM API key is required")
    try:
        parser = LLMParser(
            api_key=api_key,
            provider=req.provider,
            base_url=req.base_url,
            timeout=10.0,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        models = await parser.list_models()
    except Exception as e:
        # SDK 异常类型因提供商而异；细节进日志，响应保持通用文案
        logger.warning("LLM model list fetch failed (%s): %s", req.provider, e)
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch the model list from the provider",
        )
    finally:
        await parser.aclose()
    return LLMModelsResponse(models=models)
