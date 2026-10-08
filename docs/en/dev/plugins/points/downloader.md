# Downloader (downloader)

Adds a downloader backend. `@provider(points.DOWNLOADER, id=...)` returns a factory. The factory receives the connection parameters `DownloaderConnection` and returns a client object. The `id` is the "type" of an instance. The user adds an instance in Settings → Downloader and selects this type (config item `plugins.instances[].provider`). The built-in types are `qbittorrent`, `aria2` and `mock`.

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

## Contract

- Implement at least `CoreDownloaderClient`: `capabilities`, `auth`, `logout`, `add_torrents`. `add_torrents` returns `AddResult.ADDED`, `DUPLICATE` or `FAILED`.
- For query, rename, management (delete, pause, move, category, tags) or RSS rules, implement the full `DownloaderClient` and declare the abilities in `capabilities`. AB skips an operation that is not declared and writes a log line. It does not crash.
- If you declare an ability, you must implement its methods: `can_query` needs `torrents_info`, `torrent_exists`, `torrents_files`. `can_rename` needs `torrents_rename_file`. `can_manage` needs the delete and pause methods.
- One instance has one client object. AB reuses it across operations (one login).
- Paths are as the downloader sees them. Several instances can run together. A torrent records its own `downloader_id`, and all operations route by it.

## Tests

```python
from ab_sdk.testing import DownloaderContract

class TestMyClient(DownloaderContract):
    behavioral = False   # set True when the client talks to a working backend or a stub

    def create(self):
        ...
```

The structure checks always run. With `behavioral = True` the suite also checks login and logout, adding torrents and querying a torrent that does not exist.
