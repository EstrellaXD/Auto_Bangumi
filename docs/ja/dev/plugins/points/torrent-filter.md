# トレントフィルター (torrent.filter)

filter フックです。RSS の更新時、AB はまずトレントをルールに一致させ、次にルール自身の「除外フィルター」を適用し、最後に `torrent.filter` フックに渡します。フックが 1 つでも拒否すると、AB はそのトレントをダウンロードせず、作品にも関連付けません（除外フィルターと同じ）。ユーザーがシーズン全体を手動で「収集」するときにも適用されます。

```python
from ab_sdk import Plugin, Verdict, hook, points
from ab_sdk.ingest import BangumiInfo, Release, TorrentInfo


class OnlyHevc(Plugin):
    @hook(points.TORRENT_FILTER, priority=50)
    def check(
        self, torrent: TorrentInfo, release: Release | None, bangumi: BangumiInfo
    ) -> Verdict:
        if "HEVC" in torrent.name or "x265" in torrent.name:
            return Verdict.ok()
        return Verdict.reject("HEVC ではありません")
```

- `release` はタイトルの解析結果です。AB が解析できなかったときは `None` です。`bangumi` はルールの読み取り専用ビューです。
- `Verdict` を返します。`True` / `False` も使えますが、`Verdict.reject(reason)` の理由はログに書かれます。
- フックが失敗またはタイムアウトした場合、AB はそのトレントを通し（fail-open）、失敗はブレーカーに数えられます。
- フックは `priority` の昇順に実行されます。1 つでも拒否すると、そこで打ち切ります。

組み込みプラグイン `ingest-filters` はこの方法で実装されています。「包含フィルター」を設定すると、名前が一致するトレントだけがダウンロードされます。
