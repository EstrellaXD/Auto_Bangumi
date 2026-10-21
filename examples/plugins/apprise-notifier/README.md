# Apprise 通知

通过 [Apprise API](https://github.com/caronc/apprise-api) 服务器把通知转发到 Telegram、Discord、邮件等上百种服务。插件不依赖 `apprise` 库，只调用 HTTP 接口。

- `@provider(points.NOTIFIER, id="apprise")`：返回 `NotifierFactory`
- 填写了 Apprise URL：`POST {server}/notify/`，请求体 `{"urls", "title", "body"}`，多个 URL 以逗号拼接
- 否则使用配置键：`POST {server}/notify/{config_key}`，请求体 `{"title", "body"}`，URL 保存在服务器上
- 两者都没填时 `send` 返回 `False`，「测试」提示需要填写其中之一
- HTTP 2xx 即成功

## 准备 Apprise API 服务器

自行运行 `caronc/apprise` 容器，例如：

```bash
docker run -d --name apprise -p 8000:8000 caronc/apprise:latest
```

与 AutoBangumi 在同一 Docker 网络时，服务器地址可填 `http://apprise:8000`。使用配置键时，先在 Apprise 的网页界面（`http://<服务器>:8000/cfg/<配置键>`）保存通知 URL。

## 配置

| 字段 | 说明 |
| --- | --- |
| `server` | Apprise API 服务器地址，默认 `http://apprise:8000` |
| `urls` | 可选：Apprise URL 列表，如 `tgram://bottoken/ChatID`；填写后忽略配置键。URL 含令牌，按秘密字段处理，读取配置时每一项只返回掩码 |
| `config_key` | 可选：服务器上保存的配置键 |

## 安装

```bash
cp -r examples/plugins/apprise-notifier config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写服务器与 URL（或配置键）；再到「设置 → 通知 → 添加渠道」选择类型 `apprise`。

## 测试

```bash
cd examples/plugins/apprise-notifier && uv run pytest
```

---

基于 @LTSlw 在 [#942](https://github.com/EstrellaXD/Auto_Bangumi/pull/942) 中的实现
