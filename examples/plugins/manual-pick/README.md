# 手动选种（示例插件）

前端挂载点的演示：番剧详情页多一个「手动选种」标签，列出规则的种子，点「选用」记录选择。

用到的能力：

- 清单 `[[plugin.ui]]`，挂载点 `bangumi.detail.tab`
- 插件自己的 `api_router`（`/api/v1/plugins/manual-pick/picks/<bangumi_id>`）
- 宿主的只读 API（`/api/v1/bangumi/<id>/torrents`，经 `host.api.get`）
- 事件：路由发布 `manual-pick.picked`，组件用 `host.events.on` 订阅并刷新

## 安装

```bash
cp -r examples/plugins/manual-pick config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，再启用 `manual-pick`。

SDK 0.x 没有「让下载器下载指定种子」的接口，所以插件只记录选择，不触发下载。
示例不在 Docker 镜像内。
