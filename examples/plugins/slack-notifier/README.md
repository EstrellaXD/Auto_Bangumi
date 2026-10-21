# Slack 通知（示例插件）

把通知发到 Slack 的 [Incoming Webhook](https://api.slack.com/messaging/webhooks)。演示：

- `@provider(points.NOTIFIER, id="slack")`：返回 `NotifierFactory`
- Webhook 地址含密钥，用 `secret_field` 声明，读取配置时只返回掩码
- 只有 HTTP 2xx 且响应体为 `ok` 才算成功
- 契约套件 `NotifierContract`

## 消息格式

请求体为 `{"text": "*标题*\n正文"}`（Slack 的 mrkdwn，`&`、`<`、`>` 已转义）。配置了 `notification.base_url` 时单集通知带海报：再加 `blocks`（一段文字和一张图片），`text` 作为手机通知的摘要。海报地址必须能被 Slack 访问；Slack 取不到图片时会拒绝整条消息，插件会去掉 `blocks` 只发文字再试一次。

## 安装

```bash
cp -r examples/plugins/slack-notifier config/plugins/local/
```

在 Slack 中创建 App，开启 Incoming Webhooks 并添加到频道，复制 Webhook 地址。在「设置 → 插件」中开启「允许未签名插件」，启用并填写地址；再到「设置 → 通知 → 添加渠道」选择类型 `slack`。

## 测试

```bash
cd examples/plugins/slack-notifier && uv run pytest
```

对应 issue：[#277](https://github.com/EstrellaXD/Auto_Bangumi/issues/277)
