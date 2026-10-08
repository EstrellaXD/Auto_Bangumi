# プラグイン開発

::: warning プレビュー版 SDK
プラグイン SDK `ab_sdk` は 4.0 の間は 0.x 版で、互換性のない変更が入る場合があります。4.1 で 1.0 に固定され、以後はセマンティックバージョニングに従います。マニフェストの `sdk` フィールドで対応する SDK のバージョン範囲を宣言します。互換性のないプラグインは AB が読み込みを拒否します。
:::

プラグインは Python パッケージです（フロントエンドコンポーネントを付けることもできます）。AutoBangumi のプロセス内で動作します。ダウンローダー、通知チャンネル、検索サイト、リネーム方式を追加できます。パイプラインへのフック、イベントの購読、REST ルート、MCP ツール、設定ページの UI も提供できます。

## 5 分で始める

1. SDK とコマンドラインをインストールします。wheel は 4.0 の各 beta / 正式版の [GitHub Releases](https://github.com/EstrellaXD/Auto_Bangumi/releases) に添付されます（ファイル名は `autobangumi_sdk-<SDK バージョン>-py3-none-any.whl`）。PyPI には公開しません。詳しくは [SDK の入手](/ja/dev/plugins/sdk) を参照してください。

   ```bash
   uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
   ```

2. ひな形を作ってテストします。ひな形の `pyproject.toml` は `autobangumi-sdk` に依存しますが、このパッケージは PyPI にありません。先に `uv add` でダウンロードした wheel を指定します。

   ```bash
   ab-plugin new my-rename --kind rename   # notifier、search も選べます
   cd my-rename
   uv add ../autobangumi_sdk-0.5.0-py3-none-any.whl   # wheel の実際のパスに置き換えます
   uv run pytest                                      # ひな形にはコントラクトテストが付いています
   ```

3. ローカルの AutoBangumi にリンクし、ホットリロードを有効にします。先に AB を一度起動して、設定ディレクトリに設定ファイルを作っておきます。`--config-dir` にはこのディレクトリを指定します（ソースから実行する場合は `backend/src/config`）。

   ```bash
   ab-plugin dev . --config-dir /path/to/autobangumi/config
   ```

   AB を一度再起動します。以後は、プラグインのファイルを変更すると自動でリロードされます。
4. パッケージ化します。`ab-plugin pack .` で `dist/my-rename-0.1.0.zip` ができます。

## ドキュメント一覧

**基本**

- [SDK の入手](/ja/dev/plugins/sdk)：GitHub Release の wheel とプラグイン開発 skill

- [基本概念](/ja/dev/plugins/concepts)：`Plugin`、`ctx`、3 種類の拡張宣言、マニフェスト、分離とサーキットブレーカー
- [設定フォーム](/ja/dev/plugins/config-forms)：`config_model` が WebUI のフォームになる仕組み
- [イベント](/ja/dev/plugins/events)：システムイベント、整理イベント、独自イベント
- [フロントエンドスロット](/ja/dev/plugins/frontend-slots)：Web Components と `AbHost`
- [コマンド ab-plugin](/ja/dev/plugins/cli)：`new`、`validate`、`pack`、`dev`
- [署名と配布](/ja/dev/plugins/signing)：ローカルプラグイン、署名付きカタログ、公開手順
- [組み込みプラグイン](/ja/dev/plugins/builtin)：`rename`、`hardlink`、`ingest-filters`、`media-server-refresh`
- [サンプルプラグイン](/ja/dev/plugins/examples)

**拡張ポイント**

| 拡張ポイント | 種類 | 用途 |
| --- | --- | --- |
| [ダウンローダー](/ja/dev/plugins/points/downloader) `downloader` | Provider | 新しいダウンローダーのバックエンド |
| [通知チャンネル](/ja/dev/plugins/points/notifier) `notifier` | Provider | 新しい通知チャンネル |
| [LLM プロバイダー](/ja/dev/plugins/points/llm-provider) `llm_provider` | Provider | 新しい LLM 解析プロバイダー |
| [検索サイト](/ja/dev/plugins/points/search-site) `search_site` | Provider | 検索ボックスのサイト |
| [定期タスク](/ja/dev/plugins/points/scheduled-task) `scheduled_task` | Provider | 定期的に実行するタスク |
| [メタデータソース](/ja/dev/plugins/points/metadata-provider) `metadata_provider` | Provider | RSS 購読の「パーサー」 |
| [リネーム方式](/ja/dev/plugins/points/rename-strategy) `rename_strategy` | Provider | ファイル名の生成規則 |
| [ファイル分類](/ja/dev/plugins/points/media-files) `media_files` | Provider | トレント内のファイルを本編・字幕・無視に分類 |
| [バージョン競合ポリシー](/ja/dev/plugins/points/conflict-policy) `conflict_policy` | Provider | 新旧のトレントが同じファイル名を取り合う場合 |
| [REST ルート](/ja/dev/plugins/points/api-router) `api_router` | Provider | プラグイン独自の HTTP エンドポイント |
| [MCP ツールとリソース](/ja/dev/plugins/points/mcp) `mcp_tool` `mcp_resource` | Provider | MCP クライアントへの公開 |
| [トレントフィルター](/ja/dev/plugins/points/torrent-filter) `torrent.filter` | filter フック | トレントをダウンロードするか判定 |
| [解析結果の補正](/ja/dev/plugins/points/title-parsed) `title.parsed` | transform フック | タイトル解析結果の補正 |
| [追加リクエストの変更](/ja/dev/plugins/points/torrent-adding) `torrent.adding` | transform フック | 保存パス・カテゴリ・タグの変更 |
| [HTTP リクエスト](/ja/dev/plugins/points/http-request) `http.request` | transform フック | AB の GET リクエストに Cookie などを追加 |
| [通知メッセージテンプレート](/ja/dev/plugins/points/message-template) `message_template` | transform フック | プッシュ文面の書き換え |

プラグインはイベントの購読（`@subscribe`）と、専用のキーバリューストア・データディレクトリも使えます。
