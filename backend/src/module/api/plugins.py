import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from ab_sdk import points
from module.conf import VERSION, settings
from module.core import AppContext
from module.plugin.host import plugin_provider_ids
from module.plugin.installer import PluginInstaller
from module.plugin.loader import CATALOG_ROOT, installed_version
from module.plugin.manifest import UiSlot
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
    # 该插件当前登记的 Provider id（按扩展点，只含非空项）；未启用时为空
    providers: dict[str, list[str]]


class PluginsOverview(BaseModel):
    allow_unsigned: bool
    plugins: list[PluginInfo]


class PluginUpdate(BaseModel):
    enabled: bool | None = None
    options: dict[str, Any] | None = None


class PluginsSettingsUpdate(BaseModel):
    allow_unsigned: bool


class CatalogEntry(BaseModel):
    """签名目录里的一个插件，以及本机已安装的版本。"""

    id: str
    name: str = ""
    version: str
    kind: str = "plugin"
    extension_points: list[str] = []
    description: str = ""
    # 插件依赖的 ab_sdk 版本范围（清单中的 sdk）
    sdk: str = ""
    min_ab_version: str = "0.0.0"
    authors: list[str] = []
    permissions: list[str] = []
    has_web: bool = False
    # 源码位置：作者仓库与固定的 commit（插件市场的索引条目）
    repo: str = ""
    commit: str = ""
    # 插件在仓库中的子目录，"." 为仓库根
    path: str = "."
    readme: str = ""
    installed_version: str | None


class PluginUiSlot(BaseModel):
    plugin_id: str
    slot: UiSlot
    element: str
    # 相对插件根目录，经 GET /plugins/<plugin_id>/<entry> 获取
    entry: str
    title: dict[str, str]


# 设置页关心的、由插件提供 Provider 的扩展点
_PROVIDER_POINTS = (
    points.DOWNLOADER,
    points.NOTIFIER,
    points.SEARCH_SITE,
    points.METADATA_PROVIDER,
    points.RENAME_STRATEGY,
)

# 模块脚本要求 JavaScript MIME 类型；mimetypes 的结果依赖系统配置，这里固定
_MEDIA_TYPES = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
}


def _overview(ctx: AppContext) -> PluginsOverview:
    conf = settings.plugins
    plugins = []
    for status in ctx.plugins.statuses():
        info = vars(status) | {
            "options": mask_options(
                conf.options.get(status.id, {}), status.config_schema
            ),
            "providers": {
                point: ids
                for point in _PROVIDER_POINTS
                if (ids := plugin_provider_ids(point, status.id))
            },
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


@router.get("/catalog", response_model=list[CatalogEntry])
async def get_catalog():
    """签名目录（GitHub release ``plugins``）里可安装的插件。"""
    try:
        entries = await PluginInstaller(app_version=VERSION).fetch_catalog()
    except Exception as e:  # noqa: BLE001 - 网络或验签失败统一报 502
        logger.warning("Plugin catalog unavailable: %s", e)
        raise HTTPException(
            status_code=502, detail=f"Plugin catalog unavailable: {e}"
        ) from None
    return [
        CatalogEntry(
            **entry, installed_version=installed_version(CATALOG_ROOT, entry["id"])
        )
        for entry in entries
    ]


@router.get("/ui", response_model=list[PluginUiSlot])
async def list_plugin_ui(ctx: AppContext = Depends(get_context)):
    """已启用插件声明的前端挂载点（清单中的 ``[[plugin.ui]]``）。"""
    return [
        PluginUiSlot(plugin_id=plugin_id, **ui.model_dump())
        for plugin_id, ui in ctx.plugins.ui_slots()
    ]


@router.get("/{plugin_id}/web/{path:path}", include_in_schema=False)
async def plugin_web_file(
    plugin_id: str, path: str, ctx: AppContext = Depends(get_context)
):
    """已启用插件 ``web/`` 目录下的静态文件（前端组件的 ES module 等）。

    与其它 API 一样需要登录；浏览器的 ``<script type="module">`` / ``import()``
    是同源请求，会带上会话 cookie。
    """
    web_dir = ctx.plugins.web_dir(plugin_id)
    if web_dir is not None:
        root = web_dir.resolve()
        target = (root / path).resolve()
        # resolve() 之后再比较，``..`` 与指向目录外的符号链接都会被拒绝
        if target.is_relative_to(root) and target.is_file():
            return FileResponse(
                target,
                media_type=_MEDIA_TYPES.get(target.suffix),
                # 插件升级后文件名不变，每次都按 ETag 重新验证
                headers={"Cache-Control": "no-cache"},
            )
    raise HTTPException(status_code=404, detail="Not Found")


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


@router.post("/{plugin_id}/install", response_model=PluginsOverview)
async def install_plugin(plugin_id: str, ctx: AppContext = Depends(get_context)):
    """从签名目录安装（或升级）插件并启用：用户点安装即同意其运行。"""
    result = await PluginInstaller(app_version=VERSION).install(plugin_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    settings.plugins.enabled[plugin_id] = True
    await asyncio.to_thread(settings.save)
    # 升级时配置快照没有变化，apply_settings 不会重新加载，所以按 id 重载
    await ctx.plugins.reload(plugin_id)
    return _overview(ctx)


@router.delete("/{plugin_id}", response_model=PluginsOverview)
async def uninstall_plugin(plugin_id: str, ctx: AppContext = Depends(get_context)):
    """卸载经签名目录安装的插件；内置与本地插件不受影响。"""
    result = await PluginInstaller(app_version=VERSION).uninstall(plugin_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    await ctx.plugins.reload(plugin_id)
    return _overview(ctx)


@router.get("/providers", response_model=dict[str, list[str]])
async def list_plugin_providers():
    """插件提供的 Provider id（按扩展点），设置页把它们并入下拉候选。"""
    return {point: plugin_provider_ids(point) for point in _PROVIDER_POINTS}
