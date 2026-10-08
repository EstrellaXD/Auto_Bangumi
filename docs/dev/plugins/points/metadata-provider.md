# 元数据源（metadata_provider）

新番规则入库前，AB 按 RSS 订阅的「解析器」取值选择元数据源，补全官方标题、季度、年份和海报。内置 `mikan` 与 `tmdb`。`@provider(points.METADATA_PROVIDER, id=...)` 增加新的取值：添加订阅时，「解析器」下拉框会列出它。

```python
from dataclasses import replace

from ab_sdk import Plugin, points, provider
from ab_sdk.ingest import Metadata, MetadataRequest


class BangumiTv:
    async def enrich(self, request: MetadataRequest) -> Metadata | None:
        info = await search(request.current.official_title)  # 自己的实现
        if info is None:
            return None  # 不修改
        return replace(request.current, official_title=info.name, poster_link=info.cover)


class MyPlugin(Plugin):
    @provider(points.METADATA_PROVIDER, id="bangumi-tv")
    def bgm(self):
        return BangumiTv()
```

- `request.kind` 区分番剧（`bangumi`）与电影（`movie`），`request.torrent.homepage` 是种子的详情页，`request.language` 是语言设置。
- 返回完整的新 `Metadata`，通常基于 `request.current` 修改；返回 `None` 表示不修改。
- 失败或超时时保留原值，并计入熔断。
