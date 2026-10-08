import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

from ab_sdk import points
from module.conf import settings
from module.core import AppContext
from module.plugin.host import plugin_provider_ids
from module.plugin.secrets import mask_options, restore_options
from module.security.api import get_current_user

from .deps import get_context

router = APIRouter(
    prefix="/plugins", tags=["plugins"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger(__name__)


class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    source: str
    signed: bool
    state: str
    enabled: bool
    description: str
    permissions: list[str]
    error: str | None
    config_schema: dict[str, Any] | None
    options: dict[str, Any]


class PluginsOverview(BaseModel):
    allow_unsigned: bool
    plugins: list[PluginInfo]


class PluginUpdate(BaseModel):
    enabled: bool | None = None
    options: dict[str, Any] | None = None


class PluginsSettingsUpdate(BaseModel):
    allow_unsigned: bool


def _overview(ctx: AppContext) -> PluginsOverview:
    conf = settings.plugins
    plugins = []
    for status in ctx.plugins.statuses():
        info = vars(status) | {
            "options": mask_options(
                conf.options.get(status.id, {}), status.config_schema
            )
        }
        plugins.append(PluginInfo(**info))
    return PluginsOverview(allow_unsigned=conf.allow_unsigned, plugins=plugins)


async def _save_and_apply(ctx: AppContext) -> None:
    # 与 /config/update 相同：落盘后走 reload_settings 统一重新应用
    await asyncio.to_thread(settings.save)
    await ctx.reload_settings()


@router.get("", response_model=PluginsOverview)
async def list_plugins(ctx: AppContext = Depends(get_context)):
    """已发现的插件、运行状态、配置表单 schema 与（掩码后的）当前配置。"""
    return _overview(ctx)


@router.put("/settings", response_model=PluginsOverview)
async def update_plugins_settings(
    body: PluginsSettingsUpdate, ctx: AppContext = Depends(get_context)
):
    settings.plugins.allow_unsigned = body.allow_unsigned
    await _save_and_apply(ctx)
    return _overview(ctx)


@router.put("/{plugin_id}", response_model=PluginsOverview)
async def update_plugin(
    plugin_id: str, body: PluginUpdate, ctx: AppContext = Depends(get_context)
):
    """启用/停用插件或修改其配置；保存后立即重新应用。"""
    status = next((s for s in ctx.plugins.statuses() if s.id == plugin_id), None)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Unknown plugin: {plugin_id}")
    conf = settings.plugins
    if body.options is not None:
        options = restore_options(
            dict(body.options), conf.options.get(plugin_id, {}), status.config_schema
        )
        try:
            ctx.plugins.validate_options(plugin_id, options)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                # ctx 里可能带 ValueError 等不可 JSON 序列化的对象
                detail=e.errors(include_url=False, include_context=False),
            ) from None
        conf.options[plugin_id] = options
    if body.enabled is not None:
        conf.enabled[plugin_id] = body.enabled
    await _save_and_apply(ctx)
    return _overview(ctx)


@router.get("/providers", response_model=dict[str, list[str]])
async def list_plugin_providers():
    """插件提供的 Provider id（按扩展点），设置页把它们并入下拉候选。"""
    return {
        point: plugin_provider_ids(point)
        for point in (
            points.DOWNLOADER,
            points.NOTIFIER,
            points.SEARCH_SITE,
            points.METADATA_PROVIDER,
            points.RENAME_STRATEGY,
        )
    }
