# 検索サイト (search_site)

検索ボックスにサイトを追加します。`@provider(points.SEARCH_SITE, id=...)` は `SearchSite` を返します。`id` がサイト名です。

```python
from ab_sdk.search import SearchSite

@provider(points.SEARCH_SITE, id="my-site")
def site(self):
    return SearchSite(url="https://example.com/rss?q=%s", parser="tmdb")
```

- `url` には `%s` がちょうど 1 つ必要です。AB はこれをキーワードに置き換えます（複数の語は `+` で連結します）。
- `parser` は検索結果を補完するメタデータソースを指定します：`mikan` または `tmdb`。
- ユーザーが検索設定で設定した同名のサイトは、プラグインのサイトより優先されます。
- サイトにログインが必要なときは、[`http.request` フック](/ja/dev/plugins/points/http-request) で Cookie を付けます。

## テスト

```python
from ab_sdk.testing import SearchSiteContract, create_plugin

class TestSite(SearchSiteContract):
    def create(self):
        plugin, _ = create_plugin(MyPlugin)
        return plugin.site()
```

例：`examples/plugins/custom-rss-site`。
