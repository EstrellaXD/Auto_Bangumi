# OneBot 通知

通过 [OneBot v11](https://github.com/botuniverse/onebot-11) HTTP API 把通知发到 QQ 私聊或群。NapCat、Lagrange.OneBot、LLOneBot 等实现都提供这个接口。

- `@provider(points.NOTIFIER, id="onebot")`：返回 `NotifierFactory`
- 向 `{url}/send_private_msg`（`user_id`）或 `{url}/send_group_msg`（`group_id`）POST JSON，消息为消息段数组
- 填写了 Access Token 时附带 `Authorization: Bearer <token>`
- HTTP 2xx 且返回 `status == "ok"` 或 `retcode == 0` 才算成功

## 配置

| 字段 | 说明 |
| --- | --- |
| `url` | OneBot HTTP API 地址，如 `http://napcat:3000` |
| `access_token` | 可选：Access Token（秘密字段） |
| `message_type` | `private`（私聊）或 `group`（群聊） |
| `target` | 私聊填 QQ 号，群聊填群号 |
| `send_poster` | 是否附带海报图片，默认开启 |

## 海报

插件只能拿到宿主给出的公开海报地址，拿不到本地海报文件。因此要发送海报，需要在「设置 → 通知」中配置 `base_url`，并保证 OneBot 实现能访问这个地址；它会自行下载图片。未配置时只发送文字。

## 安装

```bash
cp -r examples/plugins/onebot-notifier config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写 API 地址与目标；再到「设置 → 通知 → 添加渠道」选择类型 `onebot`。

## 测试

```bash
cd examples/plugins/onebot-notifier && uv run pytest
```

---

基于 @AMYdd00 在 [#1033](https://github.com/EstrellaXD/Auto_Bangumi/pull/1033) 中的实现
