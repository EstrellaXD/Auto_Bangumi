"""示例插件：自定义 RSS 站点。

- ``search_site``：搜索框多出站点 ``my-tracker``。``%s`` 被替换为关键词。
- ``http.request``：宿主向该站点发 GET 请求（RSS、种子文件）时附带 Cookie，
  用于需要登录的私有站。只改本站点的请求，其它请求原样放行。
"""

from dataclasses import replace
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ab_sdk import Plugin, hook, points, provider, secret_field
from ab_sdk.ingest import HttpRequest
from ab_sdk.search import SearchSite


class Options(BaseModel):
    url: str = Field(
        "https://tracker.example.org/rss?search=%s",
        title="搜索地址",
        description="RSS 搜索地址，%s 代表关键词",
    )
    parser: str = Field("tmdb", title="元数据源", pattern="^(mikan|tmdb)$")
    cookie: str = secret_field(title="Cookie", description="私有站登录后的 Cookie")


class CustomRssSite(Plugin[Options]):
    config_model = Options

    @provider(points.SEARCH_SITE, id="my-tracker")
    def site(self) -> SearchSite:
        return SearchSite(url=self.config.url, parser=self.config.parser)

    @hook(points.HTTP_REQUEST)
    def add_cookie(self, request: HttpRequest) -> HttpRequest | None:
        cfg = self.config
        host = urlparse(cfg.url.replace("%s", "x")).hostname
        if not cfg.cookie or urlparse(request.url).hostname != host:
            return None  # None 表示不修改
        return replace(request, headers={**request.headers, "Cookie": cfg.cookie})
