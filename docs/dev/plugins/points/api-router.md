# REST 路由（api_router）

给插件增加 HTTP 接口，常用于前端组件的后端。`@provider(points.API_ROUTER, id=...)` 返回 `fastapi.APIRouter`。

```python
from fastapi import APIRouter

@provider(points.API_ROUTER, id="api")
def api(self):
    router = APIRouter()

    @router.get("/stats")
    async def stats():
        return {"count": await self.ctx.kv.get("count", 0)}

    return router
```

- 路由挂载在 `/api/v1/plugins/<插件 id>/` 下，上例为 `GET /api/v1/plugins/my-plugin/stats`。`id` 只需在插件内唯一。
- **所有插件路由都强制登录鉴权**，与 WebUI 其它接口使用同一套凭据（会话 Cookie 或 `scope=api` 的 API 令牌）。插件无法注册匿名端点，未登录返回 401。
- 路由随插件启用出现、随停用消失，无需重启。同一插件可以提供多个 `API_ROUTER`，合并到同一前缀下。
- 处理函数抛出 `HTTPException` 返回对应状态码；抛出其它异常返回 500，并计入熔断。
- 插件路由不出现在 `/docs` 里。
- 保留路径：`web/`（前端静态资源）、`install`、`catalog`（见 [签名与分发](/dev/plugins/signing)）不能用作路由路径。
