# ダウンローダー (downloader)

ダウンローダーのバックエンドを追加します。`@provider(points.DOWNLOADER, id=...)` はファクトリを返します。ファクトリは接続パラメーター `DownloaderConnection` を受け取り、クライアントオブジェクトを返します。`id` はインスタンスの「種類」です。ユーザーは設定 → ダウンローダーでインスタンスを追加し、この種類を選びます（設定項目 `plugins.instances[].provider`）。組み込みの種類は `qbittorrent`、`aria2`、`mock` です。

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

## コントラクト

- 最低限 `CoreDownloaderClient` を実装します：`capabilities`、`auth`、`logout`、`add_torrents`。`add_torrents` は `AddResult.ADDED`、`DUPLICATE`、`FAILED` のいずれかを返します。
- 照会、リネーム、管理（削除・一時停止・移動・カテゴリ・タグ）、RSS ルールが必要なときは、完全な `DownloaderClient` を実装し、`capabilities` で機能を宣言します。AB は宣言されていない操作をスキップしてログを書きます。クラッシュしません。
- 機能を宣言したら、対応するメソッドを実装する必要があります：`can_query` は `torrents_info`、`torrent_exists`、`torrents_files`、`can_rename` は `torrents_rename_file`、`can_manage` は削除や一時停止のメソッドが必要です。
- 1 つのインスタンスに 1 つのクライアントオブジェクトが対応します。AB は複数の操作でこれを再利用します（ログインは 1 回）。
- パスはダウンローダーから見たものです。複数のインスタンスを同時に動かせます。トレントは自分の `downloader_id` を記録し、すべての操作はそれで振り分けられます。

## テスト

```python
from ab_sdk.testing import DownloaderContract

class TestMyClient(DownloaderContract):
    behavioral = False   # 実際に動くバックエンドかスタブに接続できるなら True

    def create(self):
        ...
```

構造の検査は常に実行されます。`behavioral = True` にすると、ログイン / ログアウト、トレント追加、存在しないトレントの照会などの動作も検査します。
