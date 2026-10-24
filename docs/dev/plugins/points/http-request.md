# 请求头（http.request）

transform 钩子。AB 发出的 GET 请求（RSS、种子文件、站点页面）都会经过它。适合给私有站点加 Cookie 或换 User-Agent。只能修改请求头：`url` 与 `method` 的改动会被忽略。

```python
from dataclasses import replace

from pydantic import BaseModel

from ab_sdk import Plugin, hook, points, secret_field


class Options(BaseModel):
    cookie: str = secret_field(description="站点 Cookie")


class PrivateSite(Plugin[Options]):
    config_model = Options

    @hook(points.HTTP_REQUEST)
    def auth(self, request):
        if "pt.example.com" not in request.url:
            return None
        return replace(request, headers={**request.headers, "Cookie": self.config.cookie})
```

- 参数 `HttpRequest` 有 `method`、`url`、`headers`。返回修改后的副本，或 `None` 表示不修改。
- 这个钩子在每个请求上都会调用。保持轻量，不要在里面发起网络请求。
- 用 `secret_field` 保存 Cookie，WebUI 只显示掩码。

示例：`examples/plugins/custom-rss-site`。
