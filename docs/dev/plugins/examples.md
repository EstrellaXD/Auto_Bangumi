# 示例插件

示例在仓库的 [`examples/plugins/`](https://github.com/EstrellaXD/Auto_Bangumi/tree/main/examples/plugins) 下，不包含在 Docker 镜像里。每个示例都有自己的 README 和测试，CI 逐个运行。

| 示例 | 演示的能力 |
| --- | --- |
| `webhook-on-event` | `@subscribe("*")`、配置表单、`secret_field`；把选中的事件 POST 到一个 URL，可选 HMAC 签名 |
| `custom-rss-site` | `search_site` Provider 加 `http.request` 钩子；为私有站的请求附带 Cookie；`SearchSiteContract` |
| `template-rename` | `rename_strategy` Provider，自带过滤器的文件名模板；`RenameSkipped`；`RenameStrategyContract` |
| `nfo-writer` | 订阅 `torrent.organized`，在正片旁写 `.nfo`；路径映射；幂等 |
| `ntfy-notifier` | `notifier` Provider；后端拒绝时返回 `False`；`NotifierContract` |
| `wpush-notifier` | `notifier` Provider；WPUSH 多渠道推送，按返回 JSON 的 `code` 判断成败 |
| `onebot-notifier` | `notifier` Provider；OneBot v11 私聊 / 群消息，消息段附带海报 `poster_url` |
| `apprise-notifier` | `notifier` Provider；调用 Apprise API 服务器，支持 URL 列表与配置键两种方式 |
| `run-command` | 订阅 `torrent.organized` / `file.renamed`，运行外部命令；参数列表不经过 shell；环境变量与占位符；超时终止 |
| `strm-writer` | 订阅 `torrent.organized`，按媒体目录结构写 `.strm`；幂等 |
| `synology-chat-notifier` | `notifier` Provider；表单字段 `payload=<JSON>`；HTTP 200 但 `success: false` 时返回 `False` |
| `slack-notifier` | `notifier` Provider；mrkdwn 转义；带海报时附图片块 |
| `manual-pick` | 前端挂载点 `bangumi.detail.tab`、插件路由、插件 KV、事件 |

## 安装一个示例

```bash
cp -r examples/plugins/ntfy-notifier config/plugins/local/
```

在 设置 → 插件 中开启「允许未签名插件」，再启用该插件。

## 运行示例的测试

在仓库根目录运行，脚本逐个校验示例的清单并运行它的测试（与 CI 相同）：

```bash
scripts/test_example_plugins.sh
```

脚本在 `backend/` 的环境里运行，SDK 以可编辑方式装在那里。示例的 `pyproject.toml` 依赖 `autobangumi-sdk`，PyPI 上没有这个包；把示例复制到仓库外单独测试时，先在示例目录里 `uv add <轮子路径>`，再 `uv run pytest`。

刷新 Jellyfin / Emby / Plex 媒体库不需要写插件：内置插件 `media-server-refresh` 已经支持。
