# 通知設定

## WebUI

![notification](/image/config/notifier.png){width=700}{class=ab-shadow-card}

![notification provider](/image/config/notifier-provider.png){width=700}{class=ab-shadow-card}

通知は複数のproviderに対応しています。全体スイッチを有効にした後、個別providerを追加、編集、有効/無効化、削除、テストできます。変更後は **保存して再起動** をクリックしてください。

対応provider：

- Telegram
- Discord
- Bark
- Server Chan / Server Chan 3
- WeCom
- Gotify
- Pushover
- Webhook

Webhookテンプレートでは `{{title}}`、`{{season}}`、`{{episode}}`、`{{poster_url}}` などのプレースホルダーを使えます。

## `config.json`

セクション：`notification`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `enable` | 通知を有効化 | 真偽値 | 有効化 | `false` |
| `providers` | 通知provider一覧 | 配列 | provider一覧 | `[]` |
| `base_url` | ポスターURLを絶対URLにする公開URL | 文字列 | 設定ファイルのみ | `""` |

旧形式の `type`、`token`、`chat_id` は読み込み時に `providers` へ移行されます。
