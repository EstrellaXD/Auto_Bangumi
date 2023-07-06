# 通知配置

## WebUI 配置

![notification](../image/config/notifier.png)

- `type` 为通知类型，目前支持 `telegram` 、 `serverchan` 、 `bark`、 `wecom` 四种类型。
- `token` 为通知 Token，目前支持 `telegram` 、 `serverchan` 、 `bark`、 `wecom` 四种类型。
- `chat_id` 为通知 Chat ID，仅在使用 `telegram` 通知时需要填写。[Telegram Bot 获取 Chat ID][5]
- 使用`wecom`时，chat_id参数框填写自建推送的url地址，同时需要在服务端增加[图文消息][6]类型。[Wecom酱配置说明][7]


## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`notification`

| 参数名     | 参数说明       | 参数类型 | WebUI 对应选项 | 默认值      |
|---------|------------|------|------------|----------|
| enable  | 是否启用通知     | 布尔值  | 通知         | false    |
| type    | 通知类型       | 字符串  | 通知类型       | telegram |
| token   | 通知 Token   | 字符串  | 通知 Token   |
| chat_id | 通知 Chat ID | 字符串  | 通知 Chat ID |

