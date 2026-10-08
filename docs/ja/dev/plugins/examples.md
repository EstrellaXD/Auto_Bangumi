# サンプルプラグイン

サンプルはリポジトリの [`examples/plugins/`](https://github.com/EstrellaXD/Auto_Bangumi/tree/main/examples/plugins) にあります。Docker イメージには含まれません。各サンプルに README とテストがあり、CI が 1 つずつ実行します。

| サンプル | 内容 |
| --- | --- |
| `webhook-on-event` | `@subscribe("*")`、設定フォーム、`secret_field`。選んだイベントを URL に POST します。HMAC 署名は任意です |
| `custom-rss-site` | `search_site` Provider と `http.request` フック。プライベートサイトのリクエストに Cookie を付けます。`SearchSiteContract` |
| `template-rename` | `rename_strategy` Provider。独自フィルター付きのファイル名テンプレート。`RenameSkipped`。`RenameStrategyContract` |
| `nfo-writer` | `torrent.organized` を購読し、本編の隣に `.nfo` を書きます。パス変換。冪等 |
| `ntfy-notifier` | `notifier` Provider。バックエンドが拒否したときは `False` を返します。`NotifierContract` |
| `manual-pick` | フロントエンドスロット `bangumi.detail.tab`、プラグインのルート、プラグイン KV、イベント |

## サンプルをインストールする

```bash
cp -r examples/plugins/ntfy-notifier config/plugins/local/
```

設定 → プラグインで「未署名プラグインを許可」をオンにし、プラグインを有効にします。

## サンプルのテストを実行する

リポジトリのルートで実行します。スクリプトは各サンプルのマニフェストを検証し、そのテストを実行します（CI と同じ）。

```bash
scripts/test_example_plugins.sh
```

スクリプトは `backend/` の環境で動き、そこには SDK が編集可能モードでインストールされています。サンプルの `pyproject.toml` は `autobangumi-sdk` に依存しますが、このパッケージは PyPI にありません。サンプルをリポジトリの外にコピーして単独でテストする場合は、先にサンプルのディレクトリで `uv add <wheel のパス>` を実行してから `uv run pytest` を実行します。

Jellyfin / Emby / Plex のライブラリ更新にプラグインを書く必要はありません。組み込みプラグイン `media-server-refresh` が対応しています。
