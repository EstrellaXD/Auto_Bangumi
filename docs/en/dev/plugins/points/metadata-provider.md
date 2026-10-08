# Metadata Provider (metadata_provider)

Before a new series rule is saved, AB selects a metadata source with the "parser" value of the RSS subscription. The source completes the official title, season, year and poster. `mikan` and `tmdb` are built in. `@provider(points.METADATA_PROVIDER, id=...)` adds a new value. The "parser" list shows it when the user adds a subscription.

```python
from dataclasses import replace

from ab_sdk import Plugin, points, provider
from ab_sdk.ingest import Metadata, MetadataRequest


class BangumiTv:
    async def enrich(self, request: MetadataRequest) -> Metadata | None:
        info = await search(request.current.official_title)  # your own code
        if info is None:
            return None  # no change
        return replace(request.current, official_title=info.name, poster_link=info.cover)


class MyPlugin(Plugin):
    @provider(points.METADATA_PROVIDER, id="bangumi-tv")
    def bgm(self):
        return BangumiTv()
```

- `request.kind` separates a series (`bangumi`) from a movie (`movie`). `request.torrent.homepage` is the detail page of the torrent. `request.language` is the language setting.
- Return a complete new `Metadata`, usually changed from `request.current`. `None` means no change.
- On a failure or a timeout AB keeps the old value, and the failure counts toward the breaker.
