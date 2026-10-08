# Adding Request (torrent.adding)

A transform hook. AB calls it before it gives the torrents to the downloader. The parameter is `ab_sdk.ingest.AddRequest` (`bangumi`, `torrents`, `save_path`, `category`, `tags`).

```python
from dataclasses import replace

from ab_sdk import Plugin, hook, points


class Tagger(Plugin):
    @hook(points.TORRENT_ADDING)
    def tag(self, request):
        return replace(request, tags=(*request.tags, request.bangumi.official_title))
```

Notes:

- Organizing and renaming process only torrents in the `Bangumi` category. If you change `category`, AB no longer organizes these torrents.
- The tag `ab:<series id>` is how rename finds the series. If a hook removes it, AB adds it again.
- Rename finds the series and the season from the structure `<series name>/Season N` in the save path. Keep this structure when you change `save_path`.
