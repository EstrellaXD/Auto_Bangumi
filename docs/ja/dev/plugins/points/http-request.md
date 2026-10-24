# HTTP リクエスト (http.request)

transform フックです。AB が送るすべての GET リクエスト（RSS、トレントファイル、サイトのページ）がこのフックを通ります。プライベートサイトへの Cookie の追加や、User-Agent の変更に使います。変更できるのはヘッダーだけです。`url` と `method` の変更は無視されます。

```python
from dataclasses import replace

from pydantic import BaseModel

from ab_sdk import Plugin, hook, points, secret_field


class Options(BaseModel):
    cookie: str = secret_field(description="サイトの Cookie")


class PrivateSite(Plugin[Options]):
    config_model = Options

    @hook(points.HTTP_REQUEST)
    def auth(self, request):
        if "pt.example.com" not in request.url:
            return None
        return replace(request, headers={**request.headers, "Cookie": self.config.cookie})
```

- 引数 `HttpRequest` は `method`、`url`、`headers` を持ちます。変更したコピーを返します。`None` は変更なしです。
- AB はリクエストごとにこのフックを呼びます。軽く保ち、中でネットワークリクエストをしないでください。
- Cookie は `secret_field` で保存します。WebUI にはマスクだけが表示されます。

例：`examples/plugins/custom-rss-site`。
