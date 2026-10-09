# メタデータソース (metadata_provider)

新しい作品のルールを保存する前に、AB は RSS 購読の「パーサー」の値でメタデータソースを選びます。ソースは正式タイトル、シーズン、年、ポスターを補完します。`mikan` と `tmdb` が組み込みです。`@provider(points.METADATA_PROVIDER, id=...)` で新しい値を追加できます。購読の追加時に、「パーサー」の一覧に表示されます。

```python
from dataclasses import replace

from ab_sdk import Plugin, points, provider
from ab_sdk.ingest import Metadata, MetadataRequest


class BangumiTv:
    async def enrich(self, request: MetadataRequest) -> Metadata | None:
        info = await search(request.current.official_title)  # 自前の実装
        if info is None:
            return None  # 変更なし
        return replace(request.current, official_title=info.name, poster_link=info.cover)


class MyPlugin(Plugin):
    @provider(points.METADATA_PROVIDER, id="bangumi-tv")
    def bgm(self):
        return BangumiTv()
```

- `request.kind` は作品（`bangumi`）と映画（`movie`）を区別します。`request.torrent.homepage` はトレントの詳細ページ、`request.language` は言語設定です。
- 完全な新しい `Metadata` を返します。通常は `request.current` を変更して作ります。`None` は変更なしです。
- 失敗またはタイムアウトの場合、AB は元の値を保持し、失敗はブレーカーに数えられます。
