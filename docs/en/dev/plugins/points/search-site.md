# Search Site (search_site)

Adds a site to the search box. `@provider(points.SEARCH_SITE, id=...)` returns a `SearchSite`. The `id` is the site name.

```python
from ab_sdk.search import SearchSite

@provider(points.SEARCH_SITE, id="my-site")
def site(self):
    return SearchSite(url="https://example.com/rss?q=%s", parser="tmdb")
```

- `url` must have exactly one `%s`. AB replaces it with the keyword (several words are joined with `+`).
- `parser` selects the metadata source that completes the search results: `mikan` or `tmdb`.
- A site with the same name that the user set in the search settings has priority over the site from a plugin.
- If the site needs a login, add a Cookie with the [`http.request` hook](/en/dev/plugins/points/http-request).

## Tests

```python
from ab_sdk.testing import SearchSiteContract, create_plugin

class TestSite(SearchSiteContract):
    def create(self):
        plugin, _ = create_plugin(MyPlugin)
        return plugin.site()
```

Example: `examples/plugins/custom-rss-site`.
