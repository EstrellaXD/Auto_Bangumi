# 插件设置

4.0 起，下载器、重命名、通知渠道、搜索站点等功能都通过插件扩展点接入。插件的启停、配置与 Provider 选择保存在 `config.json` 的 `plugins` 配置节。

## WebUI 配置

在 **设置 → 插件** 中管理插件：

- **允许未签名插件**：本地目录（`config/plugins/local/`）与 pip 安装的插件未经签名，开启后才会加载。插件与 AutoBangumi 在同一进程中运行，拥有完整权限，只启用你信任的插件。
- **启用**：每个插件卡片上的开关。
- **配置**：展开后按插件声明的配置表单填写，点击 **保存配置**。

以上三项保存后立即生效，不需要点击底部 **保存并重启**。

插件卡片显示来源（内置、本地、pip）、运行状态（运行中、未启用、错误）与声明的权限。插件加载失败、或连续失败 5 次被自动停用时，卡片显示原因；修改该插件的配置后会重新尝试加载。

以下设置不在插件页，而在对应功能的设置分区中，随全局配置一起保存（**保存并重启**）：

- 下载器实例与默认下载器：[下载器设置](/config/downloader#多个下载器)
- 重命名方式与版本冲突策略：[番剧管理设置](/config/manager)

## 内置插件

| id | 默认 | 作用 | 说明 |
| --- | --- | --- | --- |
| `rename` | 启用 | 重命名方式 `pn`、`advance`、`template` | [番剧管理设置](/config/manager#模板重命名) |
| `ingest-filters` | 启用 | 包含过滤：配置一组正则（忽略大小写）后，只下载名称匹配任一表达式的种子；留空不过滤，对所有订阅生效 | 见下文 |
| `media-server-refresh` | 启用 | 整理完成后刷新 Jellyfin / Emby / Plex，未填写地址与 API Key 时什么也不做 | [番剧管理设置](/config/manager#媒体库刷新) |
| `hardlink` | 停用 | 把整理好的文件硬链接到媒体库 | [番剧管理设置](/config/manager#硬链接到媒体库) |

`ingest-filters` 的「包含过滤」（`include`）补充规则自带的「排除过滤」。非法正则按字面匹配。

开发插件见 [插件开发](/dev/plugins)。

## `config.json` 配置选项

配置节：`plugins`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `allow_unsigned` | 加载未签名（本地目录、pip）插件 | 布尔值 | 允许未签名插件 | `false` |
| `dev_mode` | 本地插件文件变更后自动重新加载 | 布尔值 | 暂无 WebUI 项 | `false` |
| `enabled` | 按插件 id 保存的启用开关 | 对象 | 插件卡片的启用开关 | `{}` |
| `options` | 按插件 id 保存的插件配置 | 对象 | 插件卡片的配置 | `{}` |
| `hook_order` | 按扩展点指定钩子执行顺序 | 对象 | 暂无 WebUI 项 | `{}` |
| `slots` | 各扩展点选用的 Provider | 对象 | 见下表 | 见下表 |
| `instances` | 多实例扩展点的实例列表（目前只有下载器） | 数组 | 下载器设置 | 一个 id 为 `default` 的 qBittorrent 实例 |

- `enabled` 中没有出现的插件：内置插件按清单默认启用（`hardlink` 默认停用），其它来源的插件默认停用。
- `options` 中保存的值必须通过插件配置模型的校验；在 WebUI 中保存时，不合法的配置被拒绝。密码类字段在接口返回时被掩码。
- `hook_order` 的键是钩子扩展点：`torrent.filter`、`title.parsed`、`torrent.adding`、`http.request`、`message_template`；值是插件 id 列表。列出的插件按列出的顺序最先执行，其余插件按优先级、再按插件 id 排序。

### `slots`

| 参数 | 说明 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- |
| `downloader` | 默认下载器实例 id，必须是 `instances` 中的下载器实例 | 下载器设置的 **设为默认** | `default` |
| `rename_strategy` | 重命名方式：`none`（宿主自带），`pn`、`advance`、`template`（内置插件 `rename`），或其它插件提供的方式 | 番剧管理设置的重命名方式 | `pn` |
| `conflict_policy` | 更高修订版的种子指向已有剧集时：`hold` 保留现有文件，`replace` 替换为更高修订版 | 番剧管理设置的修订版冲突处理 | `hold` |
| `media_files` | 判断种子内文件是正片还是字幕的实现，宿主自带的实现按扩展名判断 | 暂无 WebUI 项 | `default` |

选中的 Provider 没有登记（例如提供它的插件被停用或被熔断）时，`rename_strategy` 按 `none` 处理，`conflict_policy` 与 `media_files` 退回宿主自带的实现。

### `instances`

```json
"instances": [
    {
        "id": "default",
        "point": "downloader",
        "provider": "qbittorrent",
        "options": { "host": "172.17.0.1:8080", "username": "admin", "password": "adminadmin", "path": "/downloads/Bangumi", "ssl": false }
    }
]
```

| 参数 | 说明 |
| --- | --- |
| `id` | 实例 id，不能重复 |
| `point` | 扩展点，目前只有 `downloader` |
| `provider` | 实现该扩展点的 Provider id，例如 `qbittorrent`、`aria2` 或插件提供的下载器 |
| `options` | 该实例的配置，下载器的字段见 [下载器设置](/config/downloader#config-json-配置选项) |

## 从 3.3 升级

升级到 4.0 后第一次启动时，AB 把 3.3 的配置迁移到 `plugins` 配置节：

- `downloader` → `plugins.instances` 中 id 为 `default` 的下载器实例，`plugins.slots.downloader` 设为 `default`。
- `bangumi_manage.rename_method` → `plugins.slots.rename_strategy`（已废弃的 `normal` 改为 `none`）。
- `bangumi_manage.revision_conflict_policy` → `plugins.slots.conflict_policy`。

迁移前原文件备份为 `config.json.v3.bak`；已有同名备份时不覆盖，改用 `config.json.v3.bak.1`、`config.json.v3.bak.2` 等。迁移失败时（例如迁移后的配置未通过校验），AB 从备份恢复原文件并**拒绝启动**，日志写明出错的字段。修正该字段后重新启动即可。
