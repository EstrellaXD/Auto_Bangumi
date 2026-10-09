# REST ルート (api_router)

プラグインに HTTP エンドポイントを追加します。フロントエンドコンポーネントのバックエンドとしてよく使われます。`@provider(points.API_ROUTER, id=...)` は `fastapi.APIRouter` を返します。

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

- ルートは `/api/v1/plugins/<プラグイン id>/` の下にマウントされます。上の例は `GET /api/v1/plugins/my-plugin/stats` です。`id` はプラグイン内で一意であれば十分です。
- **プラグインのルートはすべてログインが必須です。** WebUI の他のエンドポイントと同じ認証情報（セッション Cookie、または `scope=api` の API トークン）を使います。プラグインは匿名のエンドポイントを登録できません。ログインしていないリクエストには 401 を返します。
- ルートは、プラグインを有効にすると現れ、無効にすると消えます。再起動は不要です。1 つのプラグインが複数の `API_ROUTER` を提供でき、AB は同じプレフィックスの下にまとめます。
- ハンドラーが `HTTPException` を送出すると、そのステータスコードを返します。それ以外の例外は 500 を返し、ブレーカーに数えられます。
- プラグインのルートは `/docs` の OpenAPI ドキュメントには表示されません。
- 予約パス：`web/`（フロントエンドの静的ファイル）、`install`、`catalog`（[署名と配布](/ja/dev/plugins/signing) を参照）はルートのパスに使えません。
