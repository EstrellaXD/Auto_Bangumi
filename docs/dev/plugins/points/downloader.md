# 下载器（downloader）

增加一个下载器后端。`@provider(points.DOWNLOADER, id=...)` 返回一个工厂：接收连接参数 `DownloaderConnection`，返回客户端对象。`id` 是实例的「类型」：用户在 设置 → 下载器 中添加实例并选择该类型（配置项 `plugins.instances[].provider`）。内置类型为 `qbittorrent`、`aria2`、`mock`。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.downloader import AddResult, DownloaderCapabilities, DownloaderConnection


class MyClient:
    capabilities = DownloaderCapabilities(
        can_query=False, can_rename=False, can_manage=False, can_rss_rules=False
    )

    def __init__(self, conn: DownloaderConnection) -> None:
        self.conn = conn  # host / username / password / ssl

    async def auth(self, retry: int = 3) -> bool: ...
    async def logout(self) -> None: ...
    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ) -> AddResult: ...


class MyPlugin(Plugin):
    @provider(points.DOWNLOADER, id="my-client")
    def client(self):
        return MyClient
```

## 契约

- 至少实现 `CoreDownloaderClient`：`capabilities`、`auth`、`logout`、`add_torrents`。`add_torrents` 返回 `AddResult.ADDED`、`DUPLICATE` 或 `FAILED`。
- 需要查询、重命名、管理（删除、暂停、移动、分类、标签）或 RSS 规则时，实现完整的 `DownloaderClient`，并在 `capabilities` 里声明对应能力。AB 跳过未声明的操作并写日志，不会崩溃。
- 声明某个能力就必须实现对应方法：`can_query` 要求 `torrents_info`、`torrent_exists`、`torrents_files`；`can_rename` 要求 `torrents_rename_file`；`can_manage` 要求删除、暂停等方法。
- 一个实例对应一个客户端对象，AB 在多次操作间复用它（只登录一次）。
- 路径是下载器视角。多个实例可以并存，种子记录自己的 `downloader_id`，所有操作按它路由。

## 测试

```python
from ab_sdk.testing import DownloaderContract

class TestMyClient(DownloaderContract):
    behavioral = False   # 连着可用后端或替身时设为 True

    def create(self):
        ...
```

结构检查总是运行。`behavioral = True` 时再检查登录登出、添加种子、查询不存在的种子等行为。
