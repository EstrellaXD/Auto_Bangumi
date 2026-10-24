# Torrent Filter (torrent.filter)

A filter hook. During an RSS refresh, AB first matches a torrent to a rule, then applies the exclude filter of the rule, and last passes the torrent to the `torrent.filter` hooks. If one hook rejects it, AB does not download the torrent and does not link it to the series (the same as the exclude filter). The hook also applies when the user collects a whole season by hand.

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
        return Verdict.reject("not HEVC")
```

- `release` is the title parse result. It is `None` when AB cannot parse the title. `bangumi` is a read-only view of the rule.
- Return a `Verdict`. `True` / `False` also work, but AB writes the reason of `Verdict.reject(reason)` to the log.
- If a hook fails or times out, AB accepts the torrent (fail-open), and the failure counts toward the breaker.
- Hooks run in ascending `priority`. One rejection stops the chain.

The built-in plugin `ingest-filters` works in this way. After you set the "include filter", AB downloads only torrents whose name matches.
