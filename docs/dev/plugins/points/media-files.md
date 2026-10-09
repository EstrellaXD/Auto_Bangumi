# 文件分类（media_files）

决定种子内哪些文件按正片、字幕重命名，哪些忽略。`@provider(points.MEDIA_FILES, id=...)` 返回 `MediaFiles`。

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

- 返回 `media`（重命名为正片）、`subtitle`（随正片重命名）或 `ignore`（不处理）。
- 宿主的实现 `default` 按扩展名判断：`.mp4`、`.mkv` 为正片，`.ass`、`.srt` 为字幕。
- 用 `plugins.slots.media_files` 选择 Provider id（默认 `default`）。选中的 id 未登记（插件停用或被熔断）时，退回 `default`。
