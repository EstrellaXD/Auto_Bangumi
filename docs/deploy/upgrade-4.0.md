# 从 3.3 升级到 4.0

4.0 是插件化重构的大版本：下载器改为可以有多个的实例，重命名、硬链接、种子过滤、媒体库刷新改由内置插件提供。第一次启动时，AB 会自动把 3.3 的配置迁移到新位置。本页说明迁移改了什么、如何升级、升级后检查什么，以及如何回滚到 3.3。

::: warning 4.0 目前是测试版
4.0 只以 `4.0.0-beta.N` 测试版发布。`latest` 镜像标签在 4.0 正式版发布前仍指向 3.3。生产环境请先完成下面的备份。
:::

## 升级前

1. **确认当前版本是 3.3.x。** 4.0 只支持从 3.3.x 升级。检测到更早版本的数据（`config/version.info` 记录的版本低于 3.3，或残留 2.x 的 `data/data.json`）时，AB 拒绝启动，并提示先升级到最新的 3.3.x 启动一次。被拒绝时 `config.json` 可能已经被改写为 4.0 格式，请先用 `config.json.v3.bak` 覆盖它，再换回 3.3.x。
2. **停止容器，备份 `config` 与 `data` 两个目录。** 回滚到 3.3 时需要这两份备份（见 [回滚到 3.3](#回滚到-3-3)）。

```shell
docker stop AutoBangumi
cp -a ${HOME}/AutoBangumi/config ${HOME}/AutoBangumi/config.bak-3.3
cp -a ${HOME}/AutoBangumi/data ${HOME}/AutoBangumi/data.bak-3.3
```

## 更换镜像标签

4.0 测试版的镜像标签：

| 标签 | 含义 |
| --- | --- |
| `4.0.0-beta.N` | 指定的测试版，例如 `4.0.0-beta.1`。**推荐**，升级与回滚都可控 |
| `dev-latest` | 最新推送的测试版。任何 `X.Y.Z-beta.N` 发布都会更新它，不只是 4.0 |
| `latest` | 最新正式版。4.0 正式版发布前仍是 3.3 |

镜像同时发布到 `ghcr.io/estrellaxd/auto_bangumi` 与 Docker Hub 的 `estrellaxd/auto_bangumi`。

Docker Compose：修改 `image` 后重新创建容器。

```yaml
services:
  AutoBangumi:
    image: "ghcr.io/estrellaxd/auto_bangumi:4.0.0-beta.1"
```

```shell
docker compose pull
docker compose up -d
```

Docker CLI：删除旧容器，用新标签和原来的参数重新运行 `docker run`。

挂载卷（`/app/config`、`/app/data`）、端口与环境变量都没有变化，4.0 没有新增环境变量。插件安装在 `config/plugins/` 下，已经包含在 `/app/config` 卷里。

### 应用内更新（3.3 测试版渠道）

3.3 中更新渠道选择「测试版」的用户，会在 **设置 → 软件更新** 看到 `4.0.0-beta.N`。4.0 的更新包要求镜像版本不低于 `4.0.0-beta.1`，3.3 镜像上点击 **立即更新** 会失败，提示镜像版本过低、需要拉取新镜像。请按上一节更换镜像标签。选择「稳定版」渠道的用户不会看到 4.0 测试版。

## 第一次启动：配置迁移

AB 在读取 `config.json` 之前检查它是不是 3.3 格式。是 3.3 格式时，先把原文件备份为 `config.json.v3.bak`，再把下列字段移到 4.0 的位置：

| 3.3 字段 | 4.0 位置 |
| --- | --- |
| `downloader` | `plugins.instances` 中 id 为 `default` 的下载器实例：`type` 变为 `provider`，其它字段（地址、用户名、密码、下载路径、SSL）放入 `options` |
| — | `plugins.slots.downloader` 设为 `"default"`（默认下载器实例） |
| `bangumi_manage.rename_method` | `plugins.slots.rename_strategy`。已废弃的 `normal` 改为语义相同的 `none` |
| `bangumi_manage.revision_conflict_policy` | `plugins.slots.conflict_policy` |
| Bark 渠道的 `token` | `device_key` |
| WeCom 渠道的 `chat_id` | `webhook_url` |

迁移前后的下载器配置示例：

::: code-group

```json [3.3]
{
  "downloader": {
    "type": "qbittorrent",
    "host": "172.17.0.1:8080",
    "username": "admin",
    "password": "adminadmin",
    "path": "/downloads/Bangumi",
    "ssl": false
  },
  "bangumi_manage": {
    "rename_method": "pn",
    "revision_conflict_policy": "hold"
  }
}
```

```json [4.0]
{
  "plugins": {
    "slots": {
      "downloader": "default",
      "rename_strategy": "pn",
      "conflict_policy": "hold"
    },
    "instances": [
      {
        "id": "default",
        "point": "downloader",
        "provider": "qbittorrent",
        "options": {
          "host": "172.17.0.1:8080",
          "username": "admin",
          "password": "adminadmin",
          "path": "/downloads/Bangumi",
          "ssl": false
        }
      }
    ]
  }
}
```

:::

示例只列出相关字段；其它设置保持原样。

- **备份不会被覆盖。** 已有 `config.json.v3.bak` 时（例如回滚到 3.3 后再次升级），新的备份另存为 `config.json.v3.bak.1`、`config.json.v3.bak.2` 等。第一份备份里是最早的 3.3 配置。
- **迁移成功**时，日志出现 `Migrated config.json to 4.0 (...); the 3.3 file is kept as config.json.v3.bak`，括号里列出被移动的字段。
- **迁移失败**时，`config.json` 保持 3.3 的内容，AB 拒绝启动，日志写明出错的字段。修正该字段后重新启动即可。
- 已经是 4.0 格式的配置不会再迁移，也不会再生成备份。
- 环境变量（`AB_DOWNLOADER_HOST`、`AB_METHOD` 等）照常生效，仍然只在没有 `config.json` 的首次启动时读取；它们的值写入默认下载器实例与 `plugins.slots`。

数据库在同一次启动中自动升级到 schema v26：新增插件存储表 `plugin_kv`，番剧、电影、RSS 订阅与种子新增 `downloader_id` 列。已有种子归属 `default` 实例；已有规则与订阅的 `downloader_id` 为空，表示跟随默认实例。

## 4.0 中改变的行为

### 多个下载器

**设置 → 下载设置** 可以添加多个下载器实例（qBittorrent、aria2 或插件提供的下载器）并指定默认实例。规则与 RSS 订阅可以选择下载器，留空时用默认实例。每个种子记录它所在的下载器，重命名与删除都在该下载器上进行。详见 [下载器设置](../config/downloader)。

### 重命名改为插件

`pn`、`advance` 与新增的 `template` 由默认启用的内置插件「重命名」（`rename`）提供，`none` 由 AB 本身提供。`pn` 与 `advance` 的输出与 3.3 逐字一致。

- `template` 用自定义模板生成文件名。保存设置时 AB 试渲染模板，不合法的模板直接拒绝保存。
- 运行时某个文件的模板渲染失败，该文件保留原名，并发送「文件未重命名」通知；不会退回 `pn`。
- 在 **设置 → 插件** 中停用「重命名」插件后，所有番剧按 `none` 处理，保留原文件名。

详见 [番剧管理设置](../config/manager)。

### 硬链接到媒体库

新增内置插件「硬链接到媒体库」（`hardlink`），**默认停用**。启用后，种子整理完成时把正片与字幕链接到媒体库目录，下载目录保持原样继续做种。

- 下载器与 AB 看到的路径不同时（例如分别运行在不同容器中），按下载器实例在 `path_map` 中配置路径映射。
- 无法创建硬链接（跨文件系统）时，默认复制文件（`cross_device: copy`）。
- 在 Docker 中，媒体库目录也要挂载进 AB 容器。要使用硬链接，请把下载目录与媒体库放在同一块盘上，并以同一个挂载点映射进容器。

详见 [番剧管理设置](../config/manager)。

### 其它内置插件

- 「种子过滤」（`ingest-filters`）默认启用。「包含过滤」留空时不过滤任何种子。
- 「媒体库刷新」（`media-server-refresh`）默认启用。填写 Jellyfin / Emby / Plex 的地址与 API Key 后才会请求刷新媒体库。

### 第三方插件

本地目录（`config/plugins/local/`）与 pip 安装的插件没有签名，需要在 **设置 → 插件** 中开启「允许未签名插件」（`plugins.allow_unsigned`）才会加载。插件开发见 [插件开发](../dev/plugins)。

### 移除的功能

- 3.2 兼容的 GET 控制端点（`/api/v1/restart`、`/start`、`/stop`、`/shutdown`）和 `GET /api/v1/auth/refresh_token`。请改用 POST。调用这些端点的脚本需要修改。
- 旧版 `experimental_openai` 配置节与通知的单渠道旧字段。3.3 已把它们迁移到 `llm` 与 `notification.providers`。

## 升级后检查

- [ ] 日志中有 `Migrated config.json to 4.0` 一行，`config` 目录中有 `config.json.v3.bak`。
- [ ] **设置 → 下载设置** 中有 id 为 `default` 的实例，地址、用户名与下载路径与 3.3 相同，并且能连接。
- [ ] 重命名方式与 3.3 相同。3.3 中的 `normal` 现在显示为 `none`，行为相同：不重命名文件。
- [ ] **设置 → 插件** 中「重命名」插件处于启用状态。
- [ ] 使用 Bark 或 WeCom 通知时，发送一条测试通知。
- [ ] 需要硬链接或媒体库刷新时，在 **设置 → 插件** 中启用并配置它们。
- [ ] 使用 3.2 的 GET 控制端点的脚本已改为 POST。

## 回滚到 3.3

::: danger 先处理 `version.info`
4.0 会在 `config/version.info` 末尾追加一行 `4.0.0-beta.N`。3.3 只比较次版本号：最后一行是 4.0 时，3.3 会把数据当作 3.0 的数据，重建全部数据表，只保留番剧规则和第一个用户，种子记录等其它数据全部丢失。回滚前必须还原 `data` 备份，或删除 `version.info` 中 4.x 的行。
:::

**有升级前的完整备份时**（推荐）：

1. 停止容器。
2. 用 `config.bak-3.3` 与 `data.bak-3.3` 替换 `config` 与 `data` 目录。
3. 把镜像标签改回 3.3（例如 `3.3.6`），重新创建容器。

升级后在 4.0 中做的修改（新番剧、新订阅、新设置）全部丢失。

**没有完整备份时：**

1. 停止容器。
2. 用 `config/config.json.v3.bak` 覆盖 `config/config.json`。3.3 不认识 `plugins.instances`，不还原时下载器设置会变成默认值。
3. 编辑 `config/version.info`，删除所有以 `4.` 开头的行，使最后一行是 3.3.x 的版本号。
4. 如果在 4.0 中使用过应用内更新，删除 `config/updates/` 目录。否则 3.3 镜像启动时会加载其中更新的 4.0 代码。
5. 把镜像标签改回 3.3（例如 `3.3.6`），重新创建容器。

这种方式保留 4.0 中新增的番剧与种子记录。3.3 忽略 4.0 新增的数据库表与列。在 4.0 中修改的设置丢失。

以后再次升级到 4.0 时，迁移会重新运行，新的备份另存为 `config.json.v3.bak.1`。
