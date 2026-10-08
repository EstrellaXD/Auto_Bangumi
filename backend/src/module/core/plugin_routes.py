"""插件 REST 路由（points.API_ROUTER）的挂载表。

FastAPI 不支持在运行时卸载路由，因此宿主只注册一个固定的分发路由
``/api/v1/plugins/{plugin_id}/{path:path}``（见 ``module/api/plugin_routes.py``，
鉴权在那里强制），再按 plugin_id 转发给这里维护的、由插件 ``APIRouter`` 组成的
ASGI 应用。插件加载/重载/停用后 :meth:`PluginRoutes.sync` 重建该表，路由随插件
出现和消失。
"""

import logging

from fastapi import APIRouter
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from ab_sdk import points
from module.plugin.registry import ExtensionRegistry, ProviderEntry
from module.plugin.runner import CircuitBreaker

logger = logging.getLogger(__name__)


class PluginRoutes:
    def __init__(self, registry: ExtensionRegistry, breaker: CircuitBreaker) -> None:
        self._registry = registry
        self._breaker = breaker
        # plugin_id -> (构建时的 Provider 登记项, 合并后的路由)
        self._apps: dict[str, tuple[tuple[ProviderEntry, ...], APIRouter]] = {}

    def sync(self) -> None:
        """按注册表重建：插件重载后登记项是新对象，据此替换为新实例的路由。"""
        grouped: dict[str, list[ProviderEntry]] = {}
        for entry in self._registry.providers(points.API_ROUTER).values():
            grouped.setdefault(entry.plugin_id, []).append(entry)
        apps: dict[str, tuple[tuple[ProviderEntry, ...], APIRouter]] = {}
        for plugin_id, entries in grouped.items():
            key = tuple(sorted(entries, key=lambda e: e.id))
            current = self._apps.get(plugin_id)
            if current is not None and current[0] == key:
                apps[plugin_id] = current
                continue
            router = self._build(plugin_id, key)
            if router is not None:
                apps[plugin_id] = (key, router)
        self._apps = apps

    def plugin_ids(self) -> list[str]:
        return sorted(self._apps)

    def _build(
        self, plugin_id: str, entries: tuple[ProviderEntry, ...]
    ) -> APIRouter | None:
        combined = APIRouter()
        for entry in entries:
            try:
                router = entry.factory()
                if not isinstance(router, APIRouter):
                    raise TypeError(f"应返回 fastapi.APIRouter，收到 {type(router)}")
                combined.include_router(router)
            except Exception as e:
                reason = f"{points.API_ROUTER} {entry.id}: {type(e).__name__}: {e}"
                logger.warning("[Plugin:%s] 路由创建失败：%s", plugin_id, reason)
                self._breaker.record_failure(plugin_id, reason)
                return None
        logger.debug("[Plugin:%s] 已挂载 %d 条路由", plugin_id, len(combined.routes))
        return combined

    async def dispatch(
        self, plugin_id: str, scope: Scope, receive: Receive, send: Send
    ) -> bool:
        """把请求交给插件路由处理；插件没有路由时返回 False（由调用方回 404）。

        ``scope`` 应已按 Starlette ``Mount`` 的约定设置好 ``root_path``，插件
        路由据此只看到 ``/api/v1/plugins/<id>`` 之后的路径。插件处理函数抛出的
        异常计入熔断后继续向上抛，由宿主的异常中间件返回 500。
        """
        found = self._apps.get(plugin_id)
        if found is None:
            return False
        app: ASGIApp = found[1]
        try:
            await app(scope, receive, send)
        except HTTPException:
            # 未匹配的路径（404/405）或插件主动抛出的 HTTP 错误，不算插件故障
            raise
        except Exception as e:
            self._breaker.record_failure(
                plugin_id, f"{points.API_ROUTER}: {type(e).__name__}: {e}"
            )
            raise
        self._breaker.record_success(plugin_id)
        return True
