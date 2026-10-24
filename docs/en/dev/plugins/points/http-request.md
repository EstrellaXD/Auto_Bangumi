# HTTP Request (http.request)

A transform hook. Every GET request that AB sends (RSS, torrent files, site pages) passes through it. Use it to add a Cookie or to change the User-Agent for a private site. You can change only the headers. AB ignores changes to `url` and `method`.

```python
from dataclasses import replace

from pydantic import BaseModel

from ab_sdk import Plugin, hook, points, secret_field


class Options(BaseModel):
    cookie: str = secret_field(description="Site Cookie")


class PrivateSite(Plugin[Options]):
    config_model = Options

    @hook(points.HTTP_REQUEST)
    def auth(self, request):
        if "pt.example.com" not in request.url:
            return None
        return replace(request, headers={**request.headers, "Cookie": self.config.cookie})
```

- The parameter `HttpRequest` has `method`, `url` and `headers`. Return a changed copy, or `None` for no change.
- AB calls this hook for each request. Keep it light. Do not make network requests in it.
- Store the Cookie with `secret_field`. The WebUI shows only a mask.

Example: `examples/plugins/custom-rss-site`.
