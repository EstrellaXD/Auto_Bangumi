# 手动选种（示例插件）

前端挂载点的演示：番剧详情页多一个「手动选种」标签，列出规则的种子，点「选用」记录选择。

用到的能力：

- 清单 `[[plugin.ui]]`，挂载点 `bangumi.detail.tab`
- 插件自己的 `api_router`（`/api/v1/plugins/manual-pick/picks/<bangumi_id>`）
- 宿主的只读 API（`/api/v1/bangumi/<id>/torrents`，经 `host.api.get`）
- 事件：路由发布 `manual-pick.picked`，组件用 `host.events.on` 订阅并刷新

## 构建前端

前端源码在 `web-src/`（TypeScript，Vite 库模式，模板来自 `webui/packages/plugin-ui/template/`），产物写到 `web/index.js`，即清单 `[[plugin.ui]]` 的 `entry`。`web/` 提交在仓库里，供本地开发和 `ab-plugin validate` 使用；插件仓库的 CI 会丢弃它并重新构建。

```bash
cd web-src && pnpm install && pnpm build
```

`@autobangumi/plugin-ui` 以 `link:` 指向仓库内的 `webui/packages/plugin-ui`（只提供类型）。

## 测试

```bash
uv run pytest -q -c pyproject.toml --rootdir . tests   # 在 backend/ 目录下运行
```

## 安装

```bash
cp -r examples/plugins/manual-pick config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，再启用 `manual-pick`。

SDK 0.x 没有「让下载器下载指定种子」的接口，所以插件只记录选择，不触发下载。
示例不在 Docker 镜像内。
