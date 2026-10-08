# 内置插件

内置插件随 AB 发布，位于 `module/plugins/builtin/`，用与第三方插件相同的 SDK 实现，可以当作写法参考。在 设置 → 插件 中启停和配置。

| id | 默认 | 作用 |
| --- | --- | --- |
| `rename` | 启用 | 重命名方式 `pn`、`advance`、`template` |
| `ingest-filters` | 启用 | 包含过滤（`torrent.filter`） |
| `media-server-refresh` | 启用 | 整理完成后刷新 Jellyfin / Emby / Plex（未填写地址和 Key 时什么也不做） |
| `hardlink` | 停用 | 把整理好的文件硬链接到媒体库 |

## rename

宿主只自带 `none`（保留原名）。`pn` 以文件名解析出的标题命名，`advance` 以番剧文件夹名命名，两者的输出与 3.x 逐字节一致。`template` 用 Jinja2 沙箱模板渲染文件名主体。

::: v-pre
模板在 设置 → 插件 → 重命名 中填写，例如 `{{ title }} - S{{ season|pad(2) }}E{{ episode|pad(2) }}`。可用变量：`title`、`bangumi_name`、`season`、`episode`、`episode_type`、`group`、`kind`、`language`。过滤器 `pad(n)` 补零并保留半集小数。保存时试渲染一次，不合法的模板被拒绝（HTTP 422）。运行时渲染失败，或结果为空、含路径分隔符时，该文件保留原名并通知，**不会退回 `pn`**。
:::

## ingest-filters

补充规则自带「排除过滤」之外的「包含过滤」：配置一组正则（忽略大小写）后，只有名称匹配任一表达式的种子才会下载。留空不过滤。非法正则按字面匹配。

## media-server-refresh

订阅 `torrent.organized` 与 `hardlink` 发布的 `hardlink.linked`（文件新放入媒体库）。收到第一个事件后等待 `delay` 秒，期间的事件合并成一次刷新请求；刷新请求发出后到达的事件再排一次。

| 选项 | 说明 |
| --- | --- |
| `server` | `jellyfin`、`emby` 或 `plex` |
| `url` | 服务器地址，如 `http://192.168.1.10:8096`（Plex 默认端口 32400）；留空则不刷新 |
| `api_key` | Jellyfin / Emby 的 API Key，或 Plex 的 `X-Plex-Token` |
| `delay` | 延迟秒数，默认 30 |

## hardlink

订阅 `torrent.organized`，把正片与字幕链接到媒体库目录，下载目录原样保留继续做种。

| 选项 | 说明 |
| --- | --- |
| `source_root` | 下载根目录（AB 本地路径）。媒体库保持与它相同的目录结构：`library_root / (文件相对 source_root 的路径)` |
| `library_root` | 媒体库目录（AB 本地路径），不能位于 `source_root` 内 |
| `path_map` | `[{downloader, from, to}]`：把下载器路径前缀 `from` 换成 AB 本地路径 `to`。`downloader` 默认为 `default`；按最长前缀匹配，未匹配的路径原样使用 |
| `cross_device` | 硬链接遇到跨文件系统（EXDEV）时：`copy`（默认）、`symlink`、`skip`（跳过并通知） |

- 首次启用时 `source_root` 与 `library_root` 尚未填写，插件显示加载失败；设置表单已出现，填写并保存后插件重新加载。
- 链接或副本先写到目标旁的临时文件，再原子地改名，复制中断不会留下半个文件。
- 媒体库中已有同名文件、但不是本插件创建的：跳过，不覆盖，并发一条 `hardlink.failed` 通知。
- 本插件之前为同一集创建的链接，在版本升级（新版本替换旧种子，规范文件名不变）后被原子替换为指向新文件的链接。
- 已链接的文件再次收到事件时不做任何事；插件在自己的键值存储里记录它创建过的目标路径。插件放置后被用户删除的文件，再次收到事件时也不重建，只有补链会重建。
- **删除种子不会删除媒体库中的链接。**
- 启用前已经下载的文件不会自动处理。在插件的设置分区点「补链已有文件」，或调用 `POST /api/v1/plugins/hardlink/backfill`：遍历 `source_root` 下的 `.mp4` / `.mkv` / `.ass` / `.srt`，返回 `{"linked", "exists", "conflict", "failed"}` 计数。

::: tip Docker
硬链接不能跨文件系统。在 Docker 中，请把下载目录与媒体库放在同一块盘上，并以**同一个挂载点**映射进 AB 容器（例如把 `/mnt/media` 整体挂载为 `/media`，下载目录与媒体库都在其下）。两个独立挂载的目录即使在同一块盘上，也会被视为不同文件系统，链接会退化为 `cross_device` 指定的行为。下载器运行在另一个容器里、看到的路径与 AB 不同时，用 `path_map` 做映射。
:::
