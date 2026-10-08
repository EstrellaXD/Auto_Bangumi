# 示例插件

示例在仓库的 [`examples/plugins/`](https://github.com/EstrellaXD/Auto_Bangumi/tree/main/examples/plugins) 下，不包含在 Docker 镜像里。每个示例都有自己的 README 和测试，CI 逐个运行。

| 示例 | 演示的能力 |
| --- | --- |
| `webhook-on-event` | `@subscribe("*")`、配置表单、`secret_field`；把选中的事件 POST 到一个 URL，可选 HMAC 签名 |
| `custom-rss-site` | `search_site` Provider 加 `http.request` 钩子；为私有站的请求附带 Cookie；`SearchSiteContract` |
| `template-rename` | `rename_strategy` Provider，自带过滤器的文件名模板；`RenameSkipped`；`RenameStrategyContract` |
| `nfo-writer` | 订阅 `torrent.organized`，在正片旁写 `.nfo`；路径映射；幂等 |
| `ntfy-notifier` | `notifier` Provider；后端拒绝时返回 `False`；`NotifierContract` |
| `manual-pick` | 前端挂载点 `bangumi.detail.tab`、插件路由、插件 KV、事件 |

## 安装一个示例

```bash
cp -r examples/plugins/ntfy-notifier config/plugins/local/
```

在 设置 → 插件 中开启「允许未签名插件」，再启用该插件。

## 运行示例的测试

```bash
cd examples/plugins/ntfy-notifier && uv run pytest
# 或一次跑完全部示例（在仓库根目录）：
scripts/test_example_plugins.sh
```

刷新 Jellyfin / Emby / Plex 媒体库不需要写插件：内置插件 `media-server-refresh` 已经支持。
