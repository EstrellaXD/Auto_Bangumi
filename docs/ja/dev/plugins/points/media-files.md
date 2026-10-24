# ファイル分類 (media_files)

トレント内のどのファイルを本編として、どのファイルを字幕としてリネームするか、どれを無視するかを決めます。`@provider(points.MEDIA_FILES, id=...)` は `MediaFiles` を返します。

```python
from ab_sdk.rename import MediaFiles, MediaKind

class ByExtension:
    def classify(self, path: str) -> MediaKind:
        if path.endswith((".mkv", ".mp4")):
            return "media"
        if path.endswith((".ass", ".srt")):
            return "subtitle"
        return "ignore"
```

- `media`（本編としてリネーム）、`subtitle`（本編と一緒にリネーム）、`ignore`（処理しない）のいずれかを返します。
- ホストの実装 `default` は拡張子で判定します：`.mp4` と `.mkv` は本編、`.ass` と `.srt` は字幕です。
- `plugins.slots.media_files` で Provider の id を選びます（既定は `default`）。選ばれた id が登録されていない場合（プラグインが無効、またはブレーカー作動中）は、`default` に戻ります。
