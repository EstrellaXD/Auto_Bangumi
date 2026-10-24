"""插件 REST 路由的分发端点：``/api/v1/plugins/{plugin_id}/{path:path}``。

鉴权在这里以路由依赖的形式强制（``get_current_user``），插件路由无法绕过，
也就无法注册匿名端点。请求转发给 ``AppContext.plugin_routes`` 中该插件的
路由；插件未启用或未提供路由时返回 404。

该路由至少需要 ``/plugins/<id>/`` 之后的一段（可为空），因此不会遮蔽
``module/api/plugins.py`` 中的 ``GET /plugins``、``PUT /plugins/settings``、
``GET /plugins/providers`` 与 ``PUT /plugins/{id}``。
"""

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from module.core import AppContext
from module.core.plugin_routes import PluginRoutes
from module.security.api import get_current_user

from .deps import get_context

router = APIRouter(prefix="/plugins", tags=["plugins"])

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class _Forward(Response):
    """把当前请求原样交给插件路由，由插件路由自己发送响应。

    请求体未被读取（端点不声明 body 参数），插件路由可以正常读取。
    """

    def __init__(self, routes: PluginRoutes, plugin_id: str, sub_path: str) -> None:
        super().__init__()
        self._routes = routes
        self._plugin_id = plugin_id
        self._sub_path = sub_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path: str = scope["path"]
        # 与 Starlette Mount 一致：path 保持完整，root_path 指向挂载前缀，
        # 插件路由按 ``path - root_path`` 匹配（即 /api/v1/plugins/<id> 之后的部分）
        child = {
            k: v
            for k, v in scope.items()
            if k not in ("route", "endpoint", "path_params", "router")
        }
        child["root_path"] = path[: len(path) - len(self._sub_path)]
        handled = await self._routes.dispatch(self._plugin_id, child, receive, send)
        if not handled:
            raise HTTPException(status_code=404, detail="Not Found")


@router.api_route(
    "/{plugin_id}/{path:path}",
    methods=_METHODS,
    dependencies=[Depends(get_current_user)],
    include_in_schema=False,
)
async def plugin_route(
    plugin_id: str, path: str, ctx: AppContext = Depends(get_context)
):
    """转发到插件 ``plugin_id`` 通过 ``points.API_ROUTER`` 提供的路由。"""
    routes = ctx.plugin_routes
    if plugin_id not in routes.plugin_ids():
        raise HTTPException(
            status_code=404, detail=f"Unknown plugin route: {plugin_id}"
        )
    return _Forward(routes, plugin_id, "/" + path)
