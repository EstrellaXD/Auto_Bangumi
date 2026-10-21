# STRM 写入（示例插件）

种子整理完成后，为每个正片写一个 `.strm`。把 STRM 目录加入 Emby / Jellyfin 媒体库，再把媒体文件放到网盘或对象存储，客户端播放时直接从该地址读取，不经过媒体服务器。演示：

- `@subscribe(TorrentOrganized.kind)`：只处理 `kind == "media"` 的文件
- 投递为「至少一次」：内容相同就不重写，`.strm` 的修改时间不变
- 文件操作放进 `asyncio.to_thread`，不阻塞事件循环

## 配置

| 字段 | 示例 | 说明 |
| --- | --- | --- |
| 媒体根目录 | `/downloads/Bangumi` | 下载器中要去掉的路径前缀（与事件路径同为下载器视角）。不在其下的文件被跳过并记录警告；填 `/` 时保留完整路径 |
| STRM 目录 | `/downloads/STRM` | 写入 `.strm` 的目录，是 AutoBangumi 看到的路径 |
| 地址前缀 | `http://nas:8096/media/` | 拼在相对路径前。含 `://` 时，路径的每一段做百分号编码（空格变为 `%20`）；不含时（如本地路径 `/mnt/cloud/`）原样拼接 |

例：正片 `/downloads/Bangumi/A/Season 1/A S01E01.mkv`，按上表配置写入 `/downloads/STRM/A/Season 1/A S01E01.strm`，内容为 `http://nas:8096/media/A/Season%201/A%20S01E01.mkv`。

前缀以 `/` 结尾时直接拼接相对路径；插件不补 `/`。字幕不写 `.strm`。

## 安装

```bash
cp -r examples/plugins/strm-writer config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写三个字段。

## 测试

```bash
cd examples/plugins/strm-writer && uv run pytest
```

对应 issue：[#428](https://github.com/EstrellaXD/Auto_Bangumi/issues/428)
