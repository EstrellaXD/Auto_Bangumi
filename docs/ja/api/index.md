# REST APIリファレンス

AutoBangumiは`/api/v1`でREST APIを公開しています。すべてのエンドポイント（ログインとセットアップを除く）はJWT認証が必要です。

**ベースURL:** `http://your-host:7892/api/v1`

**認証:** JWTトークンをCookieまたは`Authorization: Bearer <token>`ヘッダーとして含めてください。

**インタラクティブドキュメント:** 開発モードで実行している場合、Swagger UIは`http://your-host:7892/docs`で利用可能です。

---

## 認証

### ログイン

```
POST /auth/login
```

ユーザー名とパスワードで認証します。

**リクエストボディ:**
```json
{
  "username": "string",
  "password": "string"
}
```

**レスポンス:** JWTトークン付きの認証Cookieを設定します。

### トークンのリフレッシュ

```
GET /auth/refresh_token
```

現在の認証トークンをリフレッシュします。

### ログアウト

```
GET /auth/logout
```

認証Cookieをクリアしてログアウトします。

### 認証情報の更新

```
POST /auth/update
```

ユーザー名および/またはパスワードを更新します。

**リクエストボディ:**
```json
{
  "username": "string",
  "password": "string"
}
```

---

## Passkey / WebAuthn <Badge type="tip" text="v3.2+" />

WebAuthn/FIDO2 Passkeysを使用したパスワードレス認証。

### Passkeyの登録

```
POST /passkey/register/options
```

WebAuthn登録オプション（チャレンジ、リライングパーティ情報）を取得します。

```
POST /passkey/register/verify
```

ブラウザからのPasskey登録レスポンスを検証して保存します。

### Passkeyで認証

```
POST /passkey/auth/options
```

WebAuthn認証チャレンジオプションを取得します。

```
POST /passkey/auth/verify
```

Passkey認証レスポンスを検証し、JWTトークンを発行します。

### Passkeyの管理

```
GET /passkey/list
```

現在のユーザーの登録済みPasskeyをすべてリストします。

```
POST /passkey/delete
```

クレデンシャルIDで登録済みPasskeyを削除します。

---

## 設定

### 設定の取得

```
GET /config/get
```

現在のアプリケーション設定を取得します。

**レスポンス:** `program`、`downloader`、`rss_parser`、`bangumi_manager`、`notification`、`proxy`、`experimental_openai`セクションを含む完全な設定オブジェクト。

### 設定の更新

```
PATCH /config/update
```

アプリケーション設定を部分的に更新します。変更したいフィールドのみを含めてください。

**リクエストボディ:** 部分的な設定オブジェクト。

---

## 番組（アニメルール）

### すべての番組をリスト

```
GET /bangumi/get/all
```

すべてのアニメダウンロードルールを取得します。

### IDで番組を取得

```
GET /bangumi/get/{bangumi_id}
```

IDで特定のアニメルールを取得します。

### 番組の更新

```
PATCH /bangumi/update/{bangumi_id}
```

アニメルールのメタデータ（タイトル、シーズン、エピソードオフセットなど）を更新します。

### 番組の削除

```
DELETE /bangumi/delete/{bangumi_id}
```

単一のアニメルールと関連するトレントを削除します。

```
DELETE /bangumi/delete/many/
```

複数のアニメルールを一括削除します。

**リクエストボディ:**
```json
{
  "bangumi_ids": [1, 2, 3]
}
```

### 番組の無効化 / 有効化

```
DELETE /bangumi/disable/{bangumi_id}
```

アニメルールを無効化します（ファイルは保持、ダウンロード停止）。

```
DELETE /bangumi/disable/many/
```

複数のアニメルールを一括無効化します。

```
GET /bangumi/enable/{bangumi_id}
```

以前に無効化されたアニメルールを再有効化します。

### ポスターのリフレッシュ

```
GET /bangumi/refresh/poster/all
```

すべてのアニメのポスター画像をTMDBからリフレッシュします。

```
GET /bangumi/refresh/poster/{bangumi_id}
```

特定のアニメのポスター画像をリフレッシュします。

### カレンダー

```
GET /bangumi/refresh/calendar
```

Bangumi.tvからアニメ放送カレンダーデータをリフレッシュします。

### すべてリセット

```
GET /bangumi/reset/all
```

すべてのアニメルールを削除します。注意して使用してください。

---

## RSSフィード

### すべてのフィードをリスト

```
GET /rss
```

設定されたすべてのRSSフィードを取得します。

### フィードの追加

```
POST /rss/add
```

新しいRSSフィード購読を追加します。

**リクエストボディ:**
```json
{
  "url": "string",
  "aggregate": true,
  "parser": "mikan"
}
```

### フィードの有効化 / 無効化

```
POST /rss/enable/many
```

複数のRSSフィードを有効化します。

```
PATCH /rss/disable/{rss_id}
```

単一のRSSフィードを無効化します。

```
POST /rss/disable/many
```

複数のRSSフィードを一括無効化します。

### フィードの削除

```
DELETE /rss/delete/{rss_id}
```

単一のRSSフィードを削除します。

```
POST /rss/delete/many
```

複数のRSSフィードを一括削除します。

### フィードの更新

```
PATCH /rss/update/{rss_id}
```

RSSフィードの設定を更新します。

### フィードのリフレッシュ

```
GET /rss/refresh/all
```

すべてのRSSフィードのリフレッシュを手動でトリガーします。

```
GET /rss/refresh/{rss_id}
```

特定のRSSフィードをリフレッシュします。

### フィードからトレントを取得

```
GET /rss/torrent/{rss_id}
```

特定のRSSフィードから解析されたトレントのリストを取得します。

### 分析と購読

```
POST /rss/analysis
```

RSS URLを分析し、購読せずにアニメのメタデータを抽出します。

**リクエストボディ:**
```json
{
  "url": "string"
}
```

```
POST /rss/collect
```

RSSフィードからすべてのエピソードをダウンロードします（完結したアニメ用）。

```
POST /rss/subscribe
```

自動継続ダウンロード用にRSSフィードを購読します。

---

## 検索

### 番組検索（Server-Sent Events）

```
GET /search/bangumi?keyword={keyword}&provider={provider}
```

アニメのトレントを検索します。リアルタイム更新のためにServer-Sent Events（SSE）ストリームとして結果を返します。

**クエリパラメータ:**
- `keyword` — 検索キーワード
- `provider` — 検索プロバイダー（例：`mikan`、`nyaa`、`dmhy`）

**レスポンス:** 解析された検索結果を含むSSEストリーム。

### 検索プロバイダーのリスト

```
GET /search/provider
```

利用可能な検索プロバイダーのリストを取得します。

---

## プログラム制御

### ステータスの取得

```
GET /status
```

バージョン、実行状態、first_runフラグを含むプログラムステータスを取得します。

**レスポンス:**
```json
{
  "status": "running",
  "version": "3.2.0",
  "first_run": false
}
```

### プログラムの開始

```
GET /start
```

メインプログラム（RSSチェック、ダウンロード、リネーム）を開始します。

### プログラムの再起動

```
GET /restart
```

メインプログラムを再起動します。

### プログラムの停止

```
GET /stop
```

メインプログラムを停止します（WebUIはアクセス可能なまま）。

### シャットダウン

```
GET /shutdown
```

アプリケーション全体をシャットダウンします（Dockerコンテナを再起動します）。

### ダウンローダーのチェック

```
GET /check/downloader
```

設定されたダウンローダー（qBittorrent）への接続をテストします。

---

## ダウンローダー管理 <Badge type="tip" text="v3.2+" />

AutoBangumiから直接ダウンローダー内のトレントを管理します。

### トレントのリスト

```
GET /downloader/torrents
```

Bangumiカテゴリ内のすべてのトレントを取得します。

### トレントの一時停止

```
POST /downloader/torrents/pause
```

ハッシュでトレントを一時停止します。

**リクエストボディ:**
```json
{
  "hashes": ["hash1", "hash2"]
}
```

### トレントの再開

```
POST /downloader/torrents/resume
```

ハッシュで一時停止したトレントを再開します。

**リクエストボディ:**
```json
{
  "hashes": ["hash1", "hash2"]
}
```

### トレントの削除

```
POST /downloader/torrents/delete
```

オプションでファイル削除を伴うトレントを削除します。

**リクエストボディ:**
```json
{
  "hashes": ["hash1", "hash2"],
  "delete_files": false
}
```

---

## セットアップウィザード <Badge type="tip" text="v3.2+" />

これらのエンドポイントは、初回実行セットアップ中（セットアップ完了前）にのみ利用可能です。認証は**不要**です。セットアップ完了後、すべてのエンドポイントは`403 Forbidden`を返します。

### セットアップステータスの確認

```
GET /setup/status
```

セットアップウィザードが必要かどうか（初回実行）を確認します。

**レスポンス:**
```json
{
  "need_setup": true
}
```

### ダウンローダー接続のテスト

```
POST /setup/test-downloader
```

提供された認証情報でダウンローダーへの接続をテストします。

**リクエストボディ:**
```json
{
  "type": "qbittorrent",
  "host": "172.17.0.1:8080",
  "username": "admin",
  "password": "adminadmin",
  "ssl": false
}
```

### RSSフィードのテスト

```
POST /setup/test-rss
```

RSS URLがアクセス可能で解析可能か検証します。

**リクエストボディ:**
```json
{
  "url": "https://mikanime.tv/RSS/MyBangumi?token=xxx"
}
```

### 通知のテスト

```
POST /setup/test-notification
```

提供された設定でテスト通知を送信します。

**リクエストボディ:**
```json
{
  "type": "telegram",
  "token": "bot_token",
  "chat_id": "chat_id"
}
```

### セットアップの完了

```
POST /setup/complete
```

すべての設定を保存し、セットアップを完了としてマークします。センチネルファイル`config/.setup_complete`を作成します。

**リクエストボディ:** 完全な設定オブジェクト。

---

## ログ

### ログの取得

```
GET /log
```

完全なアプリケーションログファイルを取得します。

### ログのクリア

```
GET /log/clear
```

ログファイルをクリアします。

---

## レスポンス形式

すべてのAPIレスポンスは一貫した形式に従います：

```json
{
  "msg_en": "Success message in English",
  "msg_zh": "Success message in Chinese",
  "status": true
}
```

エラーレスポンスには、両方の言語でのエラーメッセージとともに適切なHTTPステータスコード（400、401、403、404、500）が含まれます。
