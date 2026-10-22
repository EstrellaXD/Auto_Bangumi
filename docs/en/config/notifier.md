# Notification Settings

## WebUI

![notification](/image/en/config/notifier.png){width=700}{class=ab-shadow-card}

![notification provider](/image/en/config/notifier-provider.png){width=700}{class=ab-shadow-card}

Notifications now support multiple providers. Enable the global switch, then add, edit, enable/disable, remove or test individual providers. Click **Save & restart** after changing notification settings.

Supported providers:

- Telegram
- Discord
- Bark
- Server Chan / Server Chan 3
- WeCom
- Gotify
- Pushover
- Webhook

Provider-specific fields include:

- Telegram: `Bot Token`, `Chat ID`
- Discord: Webhook URL
- WeCom: Webhook URL and Key
- Bark: Device Key. Optional: Server URL, sound, group, interruption level, icon URL, and the URL to open on tap
- Server Chan: SendKey
- Gotify: Server URL and App Token
- Pushover: User Key and API Token
- Webhook: Webhook URL and message template

Webhook templates can use placeholders such as `{{title}}`, `{{season}}`, `{{episode}}` and `{{poster_url}}`.

Enabled plugins can also add notification channels. They appear in the type list with the label "From plugin". The settings page does not show fields that only a plugin channel uses. If the channel needs them, add them to the provider object in `config.json`. AutoBangumi keeps them and gives them to the plugin.

## `config.json`

Section: `notification`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `enable` | Enable notifications | boolean | Enable | `false` |
| `providers` | Notification provider list | array | Provider list | `[]` |
| `base_url` | Public base URL for absolute poster URLs | string | config only | `""` |

Each object in `providers` usually contains:

| Key | Description |
| --- | --- |
| `type` | Provider type: `telegram`, `discord`, `bark`, `server-chan`, `wecom`, `gotify`, `pushover`, `webhook`, or the channel id from a plugin |
| `enabled` | Enable this provider |
| `token` | Used by Telegram (Bot Token), Server Chan (SendKey), WeCom (Key) and Gotify (App Token) |
| `chat_id` | Used by Telegram |
| `webhook_url` | Used by Discord and WeCom |
| `url` | Used by Webhook. For Bark, the URL to open on tap (optional) |
| `server_url` | Used by Bark (optional) and Gotify |
| `device_key` | Used by Bark |
| `sound` / `group` / `level` / `icon` | Optional for Bark: sound, group, interruption level (`active`, `timeSensitive`, `passive`, `critical`), and icon URL. AB does not send an empty field. When `icon` is empty, episode notifications use the poster URL |
| `user_key` / `api_token` | Used by Pushover |
| `template` | Custom message template |

On the first start after an upgrade to 4.0, the old Bark key `token` moves to `device_key`, and the old WeCom key `chat_id` moves to `webhook_url`.
