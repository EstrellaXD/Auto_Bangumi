# 种子过滤（torrent.filter）

filter 钩子。RSS 刷新时，种子先按规则匹配，再经过规则自带的「排除过滤」，最后交给 `torrent.filter` 钩子。任一钩子拒绝，该种子就不下载，也不会关联到番剧（与排除过滤相同）。手动「收集」整季时同样生效。

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
        return Verdict.reject("不是 HEVC")
```

- `release` 是标题解析结果，无法解析时为 `None`。`bangumi` 是规则的只读视图。
- 返回 `Verdict`。`True` / `False` 也可以，但 `Verdict.reject(reason)` 的原因会写进日志。
- 钩子出错或超时按放行处理（fail-open），并计入熔断。
- 多个钩子按 `priority` 升序执行，任一拒绝即短路。

内置插件 `ingest-filters` 就是这样实现的：填写「包含过滤」后，只有名称匹配的种子才会下载。
