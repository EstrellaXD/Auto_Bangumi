# NFO 写入（示例插件）

种子整理完成后，在每个正片旁写一个 Kodi / Jellyfin 格式的 `.nfo`（只含剧名、季、集）。演示：

- `@subscribe(TorrentOrganized.kind)`：事件为「至少一次」投递，插件自己保证幂等（`.nfo` 已存在就跳过）
- 事件里的路径是下载器视角，用 `path_from` / `path_to` 换成本地路径
- 文件操作放进 `asyncio.to_thread`，不阻塞事件循环

刷新媒体库不需要写插件：内置插件 `media-server-refresh` 已经支持 Jellyfin / Emby / Plex。

## 安装

```bash
cp -r examples/plugins/nfo-writer config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」并启用。

## 测试

```bash
cd examples/plugins/nfo-writer && uv run pytest
```
