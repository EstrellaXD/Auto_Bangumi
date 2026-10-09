# 搜索站点（search_site）

给搜索框增加一个站点。`@provider(points.SEARCH_SITE, id=...)` 返回 `SearchSite`，`id` 即站点名。

```python
from ab_sdk.search import SearchSite

@provider(points.SEARCH_SITE, id="my-site")
def site(self):
    return SearchSite(url="https://example.com/rss?q=%s", parser="tmdb")
```

- `url` 必须恰好含一个 `%s`，AB 把它替换为关键词（多个词用 `+` 连接）。
- `parser` 指定用哪个元数据源补全搜索结果：`mikan` 或 `tmdb`。
- 用户在搜索设置里配置的同名站点优先于插件提供的站点。
- 站点需要登录时，配合 [`http.request` 钩子](/dev/plugins/points/http-request) 附加 Cookie。

## 测试

```python
from ab_sdk.testing import SearchSiteContract, create_plugin

class TestSite(SearchSiteContract):
    def create(self):
        plugin, _ = create_plugin(MyPlugin)
        return plugin.site()
```

示例：`examples/plugins/custom-rss-site`。
