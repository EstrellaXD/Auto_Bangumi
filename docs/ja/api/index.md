# REST API リファレンス

AutoBangumi は `/api/v1` 以下で REST API を提供します。WebUI も同じ API を使います。

**ベース URL：** `http://your-host:7892/api/v1`

**対話式ドキュメント：** このページにはエンドポイントと用途だけを載せています。リクエストとレスポンスのフィールドは、動作中のインスタンスの `http://your-host:7892/docs`（FastAPI がコードから生成する Swagger UI）を参照してください。プラグインのルートは `/docs` に表示されません。

## 認証

AB は 2 種類の認証情報を受け付けます。

- **ブラウザセッション**：`POST /auth/login` にフォームフィールド `username`、`password` を送ってログインします。成功すると AB は HttpOnly Cookie `token` を設定します。WebUI はこの方法を使います。
- **API トークン**：設定 → ユーザーとアクセス制御 → API トークン で `scope=api` のトークンを作成します（または `POST /tokens` を呼びます）。平文は一度だけ表示されます。リクエストには `Authorization: Bearer <トークン>` を付けます。

```bash
curl -H "Authorization: Bearer $AB_TOKEN" http://your-host:7892/api/v1/status
```

- リクエストに `Authorization` ヘッダーがある場合、AB はそのトークンだけを検証し、Cookie は見ません。
- 認証情報がない、または無効な場合は `401` を返します。
- アカウント管理のエンドポイント（`/auth/update`、`/users`、`/tokens`、Passkey の登録と管理）はブラウザセッションだけを受け付けます。API トークンでは `403` を返します。
- 次のエンドポイントは認証不要です：`/auth/login`、`/passkey/auth/*`、セットアップウィザード `/setup/*`（`GET /setup/status` は常に使えます。その他はセットアップ完了後 `403`）、ルートパスの `/health`。
- `/auth/refresh_token` と `/auth/logout` は `Authorization` ヘッダーを見ず、セッション Cookie だけを使います。`refresh_token` は有効な Cookie がないと `401` を返します。ログインと Passkey ログインは `security.login_whitelist` で制限されます。
- ローカル開発では、環境変数 `AB_DEV_NO_AUTH=1` を設定するとすべての認証を省略します。本番環境では設定しないでください。

## 認証とアカウント

| メソッド | パス | 説明 |
| --- | --- | --- |
| `POST` | `/auth/login` | ユーザー名とパスワードでログインし、セッション Cookie を設定 |
| `POST` | `/auth/refresh_token` | 現在のセッションを延長 |
| `POST` | `/auth/logout` | 現在のセッションを終了し、Cookie を削除 |
| `GET` | `/auth/me` | 現在のユーザー |
| `POST` | `/auth/update` | 現在のアカウントを変更し、そのすべてのセッションを更新 |
| `GET` / `POST` | `/users` | ユーザーの一覧 / 作成 |
| `PATCH` / `DELETE` | `/users/{user_id}` | ユーザーの変更 / 削除 |
| `GET` / `POST` | `/tokens` | API トークンの一覧 / 作成（`scope` は `api` または `mcp`、`expires_at` は任意） |
| `DELETE` | `/tokens/{token_id}` | トークンを無効化 |
| `POST` | `/passkey/register/options`、`/passkey/register/verify` | Passkey を登録 |
| `POST` | `/passkey/auth/options`、`/passkey/auth/verify` | Passkey でログイン |
| `GET` | `/passkey/list` | 現在のユーザーの Passkey 一覧 |
| `POST` | `/passkey/delete` | Passkey を削除 |

## プログラム

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/status` | バージョン、実行状態、初回起動かどうか |
| `POST` | `/start`、`/stop`、`/restart` | バックグラウンドタスクの開始 / 停止 / 再起動 |
| `POST` | `/shutdown` | プログラムを終了 |
| `GET` | `/check/downloader` | 既定のダウンローダーが使えるか確認 |
| `GET` | `/log` | ログを読む |
| `POST` | `/log/clear` | ログを消去 |
| `GET` | `/update/check` | 最新バージョンとオンライン更新の状態 |
| `POST` | `/update/apply` | 最新の更新をダウンロードして適用し、再起動 |
| `POST` | `/update/rollback` | 前の更新に戻す。バックアップがなければイメージ付属のバージョンに戻す |
| `GET` | `/health`（ルートパス。`/api/v1` の下ではありません） | 死活監視。常に `200` を返します：`{"status", "version", "db_ok"}` |

## 設定

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/config/get` | 現在の設定。秘密フィールドはマスク済み |
| `PATCH` | `/config/update` | 設定を保存して再読み込み。マスクのまま送られた秘密フィールドは元の値を保持 |
| `POST` | `/config/llm/models` | 選択した LLM プロバイダーのモデル一覧 |
| `GET` | `/config/llm/providers` | LLM プロバイダー一覧 |
| `POST` | `/config/llm/providers/{provider_id}/install` | LLM プロバイダープラグインをインストール |
| `DELETE` | `/config/llm/providers/{provider_id}` | LLM プロバイダープラグインを削除 |
| `POST` | `/config/llm/providers/{provider_id}/auth/begin`、`/auth/complete` | サブスクリプション型プロバイダーの認可フロー |
| `GET` | `/config/llm/providers/{provider_id}/auth/status` | 認可の状態 |
| `DELETE` | `/config/llm/providers/{provider_id}/auth` | 認可を解除 |

## 番組

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/bangumi/get/all` | すべての番組ルール |
| `GET` | `/bangumi/get/{bangumi_id}` | 1 件のルール |
| `PATCH` | `/bangumi/update/{bangumi_id}` | ルールを変更 |
| `DELETE` | `/bangumi/delete/{bangumi_id}` | ルールを削除 |
| `POST` | `/bangumi/delete/many` | 一括削除 |
| `POST` | `/bangumi/disable/{bangumi_id}`、`/bangumi/enable/{bangumi_id}` | ルールの無効化 / 有効化 |
| `POST` | `/bangumi/disable/many` | 一括無効化 |
| `PATCH` | `/bangumi/archive/{bangumi_id}`、`/bangumi/unarchive/{bangumi_id}` | アーカイブ / アーカイブ解除 |
| `PATCH` | `/bangumi/{bangumi_id}/weekday` | 放送曜日を手動で設定 |
| `GET` | `/bangumi/refresh/poster/all`、`/bangumi/refresh/poster/{bangumi_id}` | ポスターを更新 |
| `GET` | `/bangumi/refresh/calendar` | 放送カレンダーを更新 |
| `GET` | `/bangumi/refresh/metadata` | TMDB メタデータを更新し、放送終了した番組を自動でアーカイブ |
| `POST` | `/bangumi/reset/all` | すべてのルールを削除 |
| `GET` | `/bangumi/needs-review` | 話数オフセットの確認が必要な番組 |
| `GET` | `/bangumi/suggest-offset/{bangumi_id}` | TMDB の話数からオフセットを提案 |
| `POST` | `/bangumi/detect-offset` | シーズン / 話数と TMDB の不一致を検出 |
| `POST` | `/bangumi/apply-offset/{bangumi_id}`、`/bangumi/apply-offset/many` | 提案されたオフセットを適用し、リネームを 1 回実行 |
| `POST` | `/bangumi/dismiss-review/{bangumi_id}` | 「要確認」の印を消す |
| `GET` / `DELETE` | `/bangumi/{bangumi_id}/torrents` | その番組のトレント記録の一覧 / 削除 |
| `DELETE` | `/bangumi/{bangumi_id}/torrents/{torrent_id}` | トレント記録を 1 件削除 |
| `GET` / `DELETE` | `/bangumi/torrents/orphans` | どの番組にも属さないトレント記録の一覧 / 削除 |
| `GET` | `/bangumi/torrents/orphans/count` | 孤立したトレント記録の件数 |
| `DELETE` | `/bangumi/torrents/orphans/{torrent_id}` | 孤立したトレント記録を 1 件削除 |

## 映画

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/movie/get/all`、`/movie/get/{movie_id}` | すべて / 1 件の映画ルール |
| `PATCH` | `/movie/update/{movie_id}` | 変更 |
| `DELETE` | `/movie/delete/{movie_id}` | 削除 |
| `DELETE` | `/movie/disable/{movie_id}` | 無効化 |
| `GET` | `/movie/enable/{movie_id}` | 有効化 |

## RSS フィード

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/rss` | すべてのフィード |
| `POST` | `/rss/add` | フィードを追加 |
| `PATCH` | `/rss/update/{rss_id}` | フィードを変更 |
| `DELETE` | `/rss/delete/{rss_id}` | フィードを削除 |
| `POST` | `/rss/delete/many` | 一括削除 |
| `PATCH` | `/rss/disable/{rss_id}` | 無効化 |
| `POST` | `/rss/disable/many`、`/rss/enable/many` | 一括無効化 / 有効化 |
| `POST` | `/rss/refresh/all`、`/rss/refresh/{rss_id}` | すぐに更新 |
| `GET` | `/rss/torrent/{rss_id}` | そのフィードのトレント |
| `POST` | `/rss/analysis` | RSS リンクを解析し、見つかった番組を返す |
| `POST` | `/rss/collect` | シーズン全体をダウンロード（収集） |
| `POST` | `/rss/subscribe` | 購読 |

## 検索

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/search/bangumi?site=<サイト>&keywords=<キーワード>` | Server-Sent Events で結果を 1 件ずつ送信。複数のキーワードは空白で区切る |
| `GET` | `/search/provider` | 使える検索サイト（プラグインが提供するサイトを含む） |
| `GET` / `PUT` | `/search/provider/config` | ユーザーが設定した検索サイトの読み込み / 保存 |

## ダウンローダー

AB 4.0 ではダウンローダーのインスタンスを複数設定できます（`plugins.instances`）。トレント一覧はすべてのインスタンスをまとめたもので、各項目に `downloader_id` が付きます。

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/downloader/instances` | ダウンローダーのインスタンス：`{"default": <既定のインスタンス id>, "instances": [{"id", "provider"}]}` |
| `GET` | `/downloader/torrents` | すべてのインスタンスのトレント。使えないインスタンスは省略 |
| `POST` | `/downloader/torrents/pause`、`/resume`、`/delete` | トレントの一時停止 / 再開 / 削除 |
| `POST` | `/downloader/torrents/tag` | トレントに番組 id のタグを付ける |
| `POST` | `/downloader/torrents/tag/auto` | タグのないトレントに、名前とパスから自動でタグを付ける |
| `GET` | `/downloader/rename-conflicts` | ユーザーの対応を待つリネームの競合 |
| `POST` | `/downloader/rename-conflicts/{operation_id}/retry` | 競合を 1 件消し、次のリネームで再確認させる |

## 通知センター

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` / `DELETE` | `/notification/messages` | アプリ内通知の一覧 / 全削除 |
| `GET` | `/notification/messages/unread-count` | 未読の件数 |
| `POST` | `/notification/messages/read-all` | すべて既読にする |
| `POST` | `/notification/messages/{message_id}/read` | 既読にする |
| `DELETE` | `/notification/messages/{message_id}` | 1 件削除 |
| `POST` | `/notification/test` | 保存済みの通知チャンネルを番号で指定してテスト |
| `POST` | `/notification/test-config` | 保存前の通知チャンネル設定をテスト |

## イベントストリーム

`GET /events/stream` は 1 本の Server-Sent Events 接続です。WebUI はポーリングの代わりにこれを使います。

| `event` | 送信のタイミング | `data` |
| --- | --- | --- |
| `status` | 3 秒ごと | `GET /status` と同じ構造 |
| `downloader` | 5 秒ごと | すべてのインスタンスのトレント。ダウンローダーが使えないときは `null` |
| `log` | 10 秒ごと | ログの末尾 |
| `update` | オンライン更新の実行中で、進捗が変わったとき | 更新の進捗 |
| `notification` | 接続したとき、および通知センターが変わったとき | 通知センターの状態（未読数 `unread_count` を含む） |
| `bus` | イベントバスにイベントが流れたとき | `{"kind": <イベント名>, "payload": {...}}`。ホストのイベントとプラグインのイベントを含む |

```bash
curl -N -H "Authorization: Bearer $AB_TOKEN" http://your-host:7892/api/v1/events/stream
```

`bus` フレームのイベント名とフィールドは [プラグイン開発 → イベント](/ja/dev/plugins/events) を参照してください。フロントエンドのプラグインコンポーネントは `host.events.on(kind, callback)` で同じフレームを受け取ります。

## プラグイン

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/plugins` | 見つかったプラグイン、状態、設定フォームの schema、現在の設定（マスク済み） |
| `PUT` | `/plugins/settings` | `allow_unsigned`（未署名プラグインを許可）を変更 |
| `PUT` | `/plugins/{plugin_id}` | プラグインの有効化 / 無効化、または設定の変更。保存するとすぐに反映。不正な設定は `422` |
| `GET` | `/plugins/providers` | プラグインが提供する Provider id（拡張ポイントごと） |
| `GET` | `/plugins/ui` | 有効なプラグインが宣言するフロントエンドスロット |
| `GET` | `/plugins/catalog` | 署名付きカタログのプラグイン。カタログを取得できないときは `502` |
| `POST` | `/plugins/{plugin_id}/install` | 署名付きカタログからプラグインをインストールまたは更新し、有効化 |
| `DELETE` | `/plugins/{plugin_id}` | 署名付きカタログからインストールしたプラグインを削除 |
| `GET` | `/plugins/{plugin_id}/web/{path}` | プラグインの `web/` ディレクトリにあるフロントエンドの静的ファイル |
| 任意 | `/plugins/{plugin_id}/{path}` | プラグイン独自のルート。[REST ルート](/ja/dev/plugins/points/api-router) を参照 |

## セットアップウィザード

これらのエンドポイントは認証不要です。`GET /setup/status` は常に使え、`need_setup`（セットアップ完了後は `false`）を返します。その他のエンドポイントは初回セットアップが完了するまでだけ使え、完了後は `403` を返します。`/setup/complete` はさらに、ブラウザーセッションか、`admin` アカウントが出荷時のパスワード `adminadmin` のままであることが必要です。それ以外は `403` を返します。

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/setup/status` | セットアップウィザードが必要か |
| `POST` | `/setup/test-downloader` | ダウンローダーへの接続をテスト |
| `POST` | `/setup/test-rss` | RSS リンクをテスト |
| `POST` | `/setup/test-notification` | テスト通知を送信 |
| `POST` | `/setup/complete` | ウィザードの設定をすべて保存し、セットアップ完了とする |

## MCP

AB はルートパスの `/mcp` 以下で MCP サーバー（SSE トランスポート）を提供します。クライアントは `GET /mcp/sse` に接続し、`POST /mcp/messages/` にメッセージを送ります。

- アクセス制御は REST API とは別です。クライアントの IP が `security.mcp_whitelist` に含まれるか、リクエストに `scope=mcp` のトークン（`Authorization: Bearer <トークン>`）が必要です。`mcp_whitelist` が空の場合、IP によるアクセスはすべて拒否されます。トークンは引き続き使えます。
- 組み込みツール：`list_anime`、`get_anime`、`search_anime`、`subscribe_anime`、`unsubscribe_anime`、`list_downloads`、`list_rss_feeds`、`get_program_status`、`refresh_feeds`、`update_anime`。
- 組み込みリソース：`autobangumi://anime/list`、`autobangumi://anime/{id}`、`autobangumi://status`、`autobangumi://rss/feeds`。
- 有効なプラグインが提供するツールの名前は `<プラグイン id>__<id>`、リソースの URI は `autobangumi://plugins/<プラグイン id>/<id>` です。[MCP ツールとリソース](/ja/dev/plugins/points/mcp) を参照してください。

## レスポンスとエラー

- 多くの操作系エンドポイントは `{"status": true, "msg_en": "...", "msg_zh": "..."}` を返します。取得系エンドポイントはデータをそのまま返します。正確な構造は `/docs` を参照してください。
- エラーには標準の HTTP ステータスコードを使います：`401` 未認証、`403` 権限なし、`404` 存在しない、`422` 検証エラー、`500` サーバーエラー。
