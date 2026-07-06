import asyncio
import logging

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


class MaskRestoreError(ValueError):
    """无法为掩码密钥可靠定位旧值来源（列表项被删/重排且身份字段同时被改）。"""


def _identity(d: dict) -> tuple:
    """列表项的身份 = 全部非敏感标量字段（敏感侧是掩码，无法参与匹配）。"""
    return tuple(
        sorted(
            (k, v)
            for k, v in d.items()
            if not isinstance(v, (dict, list)) and not _is_sensitive(k)
        )
    )


def _contains_mask(value) -> bool:
    if isinstance(value, dict):
        return any(_contains_mask(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_mask(v) for v in value)
    return value == _MASK


def _restore_masked_list(incoming: list, current: list) -> None:
    """按身份匹配列表项后再恢复各自的掩码密钥。

    掩码恢复不能盲目按下标：删掉第 0 个通知渠道后，幸存渠道的 ``********``
    会从被删渠道取值——密钥被静默写坏且原值永久丢失。只有含掩码的项才
    需要配对（新增项带明文密钥，不参与、也不许抢占候选）。长度未变时视为
    原地编辑：同下标同身份 → 唯一身份（识别重排）→ 按下标兜底；长度变了
    （增/删）只接受唯一身份匹配——包括"两项身份完全相同、删了其中一个"
    的场景在内，凡无法唯一定位来源的掩码项直接报错，绝不猜。
    """
    masked = [
        i
        for i, item in enumerate(incoming)
        if isinstance(item, dict) and _contains_mask(item)
    ]
    if not masked:
        return
    unconsumed = {j for j, item in enumerate(current) if isinstance(item, dict)}
    matched: dict[int, int] = {}

    def match_unique_identity(i: int) -> None:
        candidates = [
            j for j in unconsumed if _identity(current[j]) == _identity(incoming[i])
        ]
        if len(candidates) == 1:
            matched[i] = candidates[0]
            unconsumed.discard(candidates[0])

    if len(incoming) == len(current):
        for i in masked:
            if i in unconsumed and _identity(incoming[i]) == _identity(current[i]):
                matched[i] = i
                unconsumed.discard(i)
        for i in masked:
            if i not in matched:
                match_unique_identity(i)
        for i in masked:
            if i not in matched and i in unconsumed:
                matched[i] = i
                unconsumed.discard(i)
    else:
        for i in masked:
            match_unique_identity(i)

    for i in masked:
        if i in matched:
            _restore_masked(incoming[i], current[matched[i]])
        else:
            raise MaskRestoreError(
                f"cannot determine which stored entry list item #{i} refers to; "
                "re-enter its secret value and save again"
            )


def _restore_masked(incoming: dict, current: dict) -> dict:
    """Replace masked sentinel values with real values from current config."""
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(current.get(k), dict):
            _restore_masked(v, current[k])
        elif isinstance(v, list) and isinstance(current.get(k), list):
            _restore_masked_list(v, current[k])
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
    except MaskRestoreError as e:
        logger.warning(e)
        return JSONResponse(
            status_code=400,
            content={
                "msg_en": str(e),
                "msg_zh": "无法恢复被掩码的密钥来源，请重新输入该密钥后再保存。",
            },
        )
    except Exception as e:
        logger.warning(e)
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Update config failed.", "msg_zh": "更新配置失败。"},
        )


class LLMModelsRequest(BaseModel):
    provider: str = "openai"
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
        # 按提供商取已保存密钥（providers[id] 覆盖 → 扁平字段兜底）
        api_key, _, _ = settings.llm.effective(req.provider)
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
