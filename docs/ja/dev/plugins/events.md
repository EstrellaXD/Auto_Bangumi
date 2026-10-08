# イベント

イベントは凍結された dataclass です。クラス変数 `kind` がイベント名です。ホストとプラグインは 1 つのイベントバスを共有します。

```python
from ab_sdk import subscribe
from ab_sdk.events import RssFailureEvent

@subscribe("rss_failure")
async def on_rss_failure(self, event: RssFailureEvent):
    self.ctx.log.warning("購読 %s が失敗しました：%s", event.rss_name, event.error)
```

- 購読者は専用のキューで、発行順に非同期で実行されます。失敗やタイムアウトは発行側に影響せず、プラグインのブレーカーに数えられます。既定のタイムアウトは 30 秒です。大きなファイルのコピーのような長い処理には `@subscribe(kind, timeout=600)` を使います。
- `"*"` は全イベントを購読します。
- 発行は `self.ctx.bus.publish(event)` で行います。プラグインのイベントの `kind` は `<プラグイン id>.` で始める必要があります。ホストのイベントとの衝突を防ぐためです。
- フロントエンドコンポーネントは `host.events.on(kind, callback)` で同じバスを購読します。コールバックはイベントのフィールドを受け取ります（[フロントエンドスロット](/ja/dev/plugins/frontend-slots) を参照）。

## システムイベント

AB が通知センターに送るイベントは、すべて `ab_sdk.events.SystemEvent` のサブクラスです。`severity`、`payload()`、`describe()`（既定の中国語タイトルと本文）、`i18n()`（フロントエンドの i18n キーと引数）を持ちます。AB はまず通知センターに書き込み、次にイベントバスへ発行し、最後に外部チャンネルへプッシュします。「通知」スイッチが影響するのは外部へのプッシュだけです。プラグインは常にイベントを受け取ります。

| kind | イベントクラス | 発行のタイミング |
| --- | --- | --- |
| `rss_failure` | `RssFailureEvent` | RSS 購読が正常から接続異常に変わったとき |
| `download_failure` | `DownloadFailureEvent` | リトライ後もトレントの追加に失敗したとき |
| `offset_review` | `OffsetReviewEvent` | 作品のシーズン / 話数オフセットの確認が必要なとき |
| `downloader_unavailable` | `DownloaderUnavailableEvent` | ダウンローダーに接続できない、認証情報が違う、IP が遮断された。各インスタンスが利用可能から利用不可に変わるたびに 1 回 |
| `update_available` | `UpdateAvailableEvent` | 新しいバージョンを検出したとき |
| `update_applied` / `update_failed` | `UpdateAppliedEvent` | オンライン更新が成功 / 失敗したとき |
| `llm_auth_failure` | `LLMAuthFailureEvent` | サブスクリプション型 LLM プロバイダーの認証情報が無効になったとき |
| `llm_plugin_install_failed` | `LLMPluginInstallFailedEvent` | LLM プラグインのインストールに失敗したとき |
| `rename_conflict` | `RenameConflictEvent` | メディアファイルのリネームで保存先が競合したとき |
| `rename_skipped` | `RenameSkippedEvent` | リネーム方式がファイル名を決められず、元の名前のままにしたとき |
| `plugin.loaded` | `PluginLoaded` | プラグインの読み込みに成功したとき |
| `plugin.disabled` | `PluginDisabled` | プラグインの読み込みに失敗した、またはブレーカーが作動したとき |

システムイベントの `kind` は 3.x の値のままです（通知センターはこれで保存と翻訳を行います）。そのため `.` のプレフィックスはありません。

## 整理イベント

| kind | イベントクラス | フィールド | 発行のタイミング |
| --- | --- | --- | --- |
| `file.renamed` | `FileRenamed` | `bangumi_id`、`old_path`、`new_path`、`file_kind`、`downloader_id` | ファイルが実際にリネームされたとき（バージョン置換後のリネームを含む） |
| `torrent.organized` | `TorrentOrganized` | `torrent_hash`、`bangumi_id`、`files`（`OrganizedFile(path, kind)` のタプル）、`downloader_id` | トレントの整理が完了したとき。リネーム方式が `none` でも発行され、`files` は元のパスです |

- パスは**ダウンローダーから見た**絶対パスで、`/` で連結されます（Windows ダウンローダーの `\` も `/` に統一されます）。AB とダウンローダーで見えるディレクトリが異なる場合（別々のコンテナで動作している場合など）は、購読者側でパスを変換する必要があります。
- `bangumi_id` はトレントの `ab:<id>` タグに由来します。古いトレントでは `None` の場合があります。`downloader_id` はトレントがあるダウンローダーインスタンスの id です。インスタンスごとにパスの見え方が異なることがあります。
- `torrent.organized` の配信は**少なくとも 1 回**（at-least-once）です。「リネーム済み」タグのないトレント（リネーム方式が `none` の場合など）は、AB を再起動するたびにもう一度発行されます。購読者は冪等にしてください。
- この 2 つのイベントはイベントバスにだけ発行されます。通知センターには入りません。

## 独自イベント

通常のイベントは `Event` を継承して定義します。通知できるイベントは `SystemEvent` を継承します。発行すると、ホストのイベントと同じ経路をたどります。通知センターへの書き込み（フロントエンドに翻訳がなければ `describe()` のタイトルと本文を表示）、イベントバスへの発行、外部チャンネルへのプッシュです。`dedup_key()` が同じイベントは、通知センターで 1 件にまとめられます。

```python
from dataclasses import dataclass
from typing import ClassVar
from ab_sdk.events import SystemEvent

@dataclass(frozen=True, slots=True)
class SyncFailed(SystemEvent):
    kind: ClassVar[str] = "my-plugin.sync_failed"
    severity: ClassVar[str] = "warning"
    reason: str

    def describe(self) -> tuple[str, str]:
        return ("同期に失敗しました", self.reason)
```

組み込みの `hardlink` の `hardlink.failed` も、この方法で発行しています。
