# Notification Settings

## WebUI

![notification](/image/config/notifier.png){width=700}{class=ab-shadow-card}

![notification provider](/image/config/notifier-provider.png){width=700}{class=ab-shadow-card}

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
- Discord / WeCom: Webhook URL
- Bark: Device Key and optional Server URL
- Server Chan: SendKey
- Gotify: Server URL and App Token
- Pushover: User Key and API Token
- Webhook: Webhook URL and message template

Webhook templates can use placeholders such as `{{title}}`, `{{season}}`, `{{episode}}` and `{{poster_url}}`.

## `config.json`

Section: `notification`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `enable` | Enable notifications | boolean | Enable | `false` |
| `providers` | Notification provider list | array | Provider list | `[]` |
| `base_url` | Public base URL for absolute poster URLs | string | config only | `""` |

Legacy `type`, `token` and `chat_id` single-provider configs are still read and migrated into `providers`.
