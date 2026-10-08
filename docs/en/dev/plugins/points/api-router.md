# REST Routes (api_router)

Adds HTTP endpoints to a plugin. They are often the backend of a frontend component. `@provider(points.API_ROUTER, id=...)` returns a `fastapi.APIRouter`.

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

- AB mounts the routes under `/api/v1/plugins/<plugin id>/`. The example above is `GET /api/v1/plugins/my-plugin/stats`. The `id` must be unique only inside the plugin.
- **All plugin routes require a login.** They use the same credentials as the other WebUI endpoints (a session cookie or an API token with `scope=api`). A plugin cannot register an anonymous endpoint. A request without a login gets 401.
- Routes appear when the plugin is enabled and disappear when it is disabled. No restart is necessary. One plugin can provide several `API_ROUTER` items. AB merges them under the same prefix.
- A handler that raises `HTTPException` returns that status code. Any other exception returns 500 and counts toward the breaker.
- Plugin routes are not in the OpenAPI document at `/docs`.
- Reserved paths: `web/` (frontend static files), `install` and `catalog` (see [Signing and distribution](/en/dev/plugins/signing)) cannot be route paths.
