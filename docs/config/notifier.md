# 通知设置

## WebUI 配置

![notification](/image/config/notifier.png){width=700}{class=ab-shadow-card}

![notification provider](/image/config/notifier-provider.png){width=700}{class=ab-shadow-card}

通知设置支持多个通知服务。启用总开关后，可以添加、编辑、启用/禁用、删除和测试单个 provider。修改通知设置后，需要点击底部 **保存并重启**。

当前支持的通知服务：

- Telegram
- Discord
- Bark
- Server Chan / Server 酱³
- WeCom / 企业微信
- Gotify
- Pushover
- Webhook

不同 provider 需要的字段不同：

- Telegram：`Bot Token`、`Chat ID`
- Discord：Webhook URL
- WeCom：Webhook URL、Key
- Bark：Device Key，可选 Server URL
- Server Chan：SendKey
- Gotify：Server URL、App Token
- Pushover：User Key、API Token
- Webhook：Webhook URL、消息模板

Webhook 模板可以使用 `{{title}}`、`{{season}}`、`{{episode}}`、`{{poster_url}}` 等占位符。非 Webhook provider 会把模板渲染为普通文本。

已启用的插件也可以提供通知渠道，它们以「插件提供」标注出现在类型列表中。设置页不显示插件渠道的专用字段；需要时请在 `config.json` 中该 provider 对象里填写，AB 原样保存并传给插件。

## `config.json` 配置选项

配置节：`notification`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `enable` | 启用通知系统 | 布尔值 | 启用 | `false` |
| `providers` | 通知服务列表 | 数组 | 通知服务列表 | `[]` |
| `base_url` | 生成通知海报绝对地址时使用的公开 URL | 字符串 | 暂无 WebUI 项 | `""` |

`providers` 中的单个对象通常包含：

| 参数 | 说明 |
| --- | --- |
| `type` | provider 类型：`telegram`、`discord`、`bark`、`server-chan`、`wecom`、`gotify`、`pushover`、`webhook`，或插件提供的渠道 id |
| `enabled` | 是否启用该 provider |
| `token` | Telegram（Bot Token）、Server Chan（SendKey）、WeCom（Key）、Gotify（App Token）使用 |
| `chat_id` | Telegram 使用 |
| `webhook_url` | Discord、WeCom 使用 |
| `url` | Webhook 使用 |
| `server_url` | Bark（可选）、Gotify 使用 |
| `device_key` | Bark 使用 |
| `user_key` / `api_token` | Pushover 使用 |
| `template` | 自定义通知模板 |

升级到 4.0 后第一次启动时，Bark 的旧字段 `token` 迁移到 `device_key`，WeCom 的旧字段 `chat_id` 迁移到 `webhook_url`。
