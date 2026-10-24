# Media Files (media_files)

Decides which files in a torrent AB renames as media, which as subtitles, and which AB ignores. `@provider(points.MEDIA_FILES, id=...)` returns a `MediaFiles`.

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

- Return `media` (rename as media), `subtitle` (renamed together with the media) or `ignore` (not processed).
- The host implementation `default` uses the extension: `.mp4` and `.mkv` are media, `.ass` and `.srt` are subtitles.
- `plugins.slots.media_files` selects the Provider id (default `default`). If the selected id is not registered (the plugin is disabled or tripped), AB uses `default`.
