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

有効なプラグインも通知チャンネルを追加できます。種類の一覧に「From plugin」のラベル付きで表示されます。プラグインチャンネル固有の項目は設定画面に表示されません。必要な場合は `config.json` の該当 provider オブジェクトに記入してください。AutoBangumi はそのまま保存してプラグインに渡します。

## `config.json`

セクション：`notification`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `enable` | 通知を有効化 | 真偽値 | 有効化 | `false` |
| `providers` | 通知provider一覧 | 配列 | provider一覧 | `[]` |
| `base_url` | ポスターURLを絶対URLにする公開URL | 文字列 | 設定ファイルのみ | `""` |

`providers` の各オブジェクトには通常次の項目があります。

| キー | 説明 |
| --- | --- |
| `type` | provider の種類：`telegram`、`discord`、`bark`、`server-chan`、`wecom`、`gotify`、`pushover`、`webhook`、またはプラグインのチャンネル id |
| `enabled` | この provider を有効にする |
| `token` | Telegram（Bot Token）、Server Chan（SendKey）、WeCom（Key）、Gotify（App Token）で使用 |
| `chat_id` | Telegram で使用 |
| `webhook_url` | Discord、WeCom で使用 |
| `url` | Webhook で使用 |
| `server_url` | Bark（任意）、Gotify で使用 |
| `device_key` | Bark で使用 |
| `user_key` / `api_token` | Pushover で使用 |
| `template` | カスタム通知テンプレート |

4.0 へのアップグレード後の初回起動時に、Bark の旧項目 `token` は `device_key` へ、WeCom の旧項目 `chat_id` は `webhook_url` へ移行されます。
