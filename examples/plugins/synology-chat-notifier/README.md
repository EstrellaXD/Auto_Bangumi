# Synology Chat 通知（示例插件）

把通知发到群晖 Synology Chat 的传入 Webhook。演示：

- `@provider(points.NOTIFIER, id="synology-chat")`：返回 `NotifierFactory`
- Webhook 地址含 token，用 `secret_field` 声明，读取配置时只返回掩码
- 后端返回 HTTP 200 但 `{"success": false}` 时，`send` 同样返回 `False`
- 契约套件 `NotifierContract`

## 获取 Webhook 地址

在 Synology Chat 中打开「整合 → 传入 Webhook」，新建一个并复制地址（形如 `https://<nas>:5001/webapi/entry.cgi?api=SYNO.Chat.External&method=incoming&version=2&token=...`）。

请求为表单字段 `payload=<JSON>`，JSON 为 `{"text": "标题\n正文"}`；配置了 `notification.base_url` 时单集通知带海报地址 `file_url`，Chat 会下载并显示该图片，所以海报地址必须能被 NAS 访问。

## 安装

```bash
cp -r examples/plugins/synology-chat-notifier config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写 Webhook 地址；再到「设置 → 通知 → 添加渠道」选择类型 `synology-chat`。

## 测试

```bash
cd examples/plugins/synology-chat-notifier && uv run pytest
```

对应 issue：[#887](https://github.com/EstrellaXD/Auto_Bangumi/issues/887)
