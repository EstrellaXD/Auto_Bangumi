# 修改添加请求（torrent.adding）

transform 钩子。在种子交给下载器之前调用，参数是 `ab_sdk.ingest.AddRequest`（`bangumi`、`torrents`、`save_path`、`category`、`tags`）。

```python
from dataclasses import replace

from ab_sdk import Plugin, hook, points


class Tagger(Plugin):
    @hook(points.TORRENT_ADDING)
    def tag(self, request):
        return replace(request, tags=(*request.tags, request.bangumi.official_title))
```

注意：

- 整理与重命名只处理 `Bangumi` 分类下的种子。修改 `category` 等于让 AB 不再整理这些种子。
- `ab:<番剧 id>` 标签用于重命名时定位番剧。钩子删掉它时 AB 会补回。
- 重命名从保存路径的 `<番剧名>/Season N` 结构推断番剧与季度。修改 `save_path` 时请保留这一结构。
