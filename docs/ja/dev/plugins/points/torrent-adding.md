# 追加リクエストの変更 (torrent.adding)

transform フックです。AB がトレントをダウンローダーに渡す前に呼びます。引数は `ab_sdk.ingest.AddRequest`（`bangumi`、`torrents`、`save_path`、`category`、`tags`）です。

```python
from dataclasses import replace

from ab_sdk import Plugin, hook, points


class Tagger(Plugin):
    @hook(points.TORRENT_ADDING)
    def tag(self, request):
        return replace(request, tags=(*request.tags, request.bangumi.official_title))
```

注意点：

- 整理とリネームの対象は、`Bangumi` カテゴリのトレントだけです。`category` を変えると、AB はそのトレントを整理しなくなります。
- タグ `ab:<作品 id>` は、リネーム時に作品を見つけるために使われます。フックが削除しても、AB が付け直します。
- リネームは、保存パスの `<作品名>/Season N` という構造から作品とシーズンを判断します。`save_path` を変更するときはこの構造を保ってください。
