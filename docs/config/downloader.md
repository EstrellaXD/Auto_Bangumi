# 下载器设置

## WebUI 配置

![downloader](/image/config/downloader.png){width=700}{class=ab-shadow-card}

![downloader type](/image/config/downloader-type.png){width=700}{class=ab-shadow-card}

- **下载器类型**：支持 `qbittorrent` 与 `aria2`。
- **下载器地址**：下载器 Web API 或 RPC 地址。[详见下方说明](#下载器地址)
- **用户名 / 密码**：qBittorrent 使用 WebUI 账户密码；aria2 会忽略用户名，并把密码栏作为 RPC secret。
- **下载地址**：下载器中的保存路径，必须与下载器容器或宿主机看到的路径一致。[详见下方说明](#下载路径问题)
- **SSL**：连接下载器时使用 HTTPS。

修改下载器设置后，需要点击底部的 **保存并重启**。保存后下载器连接会重新建立。

## 多个下载器

设置页顶部列出所有下载器实例。点击一个实例即可在下方编辑它；输入新的 id 后点击 **添加** 新建实例，类型可以选 qBittorrent、aria2 或插件提供的下载器。**设为默认** 改变默认实例，默认实例不能删除。

- 规则编辑（高级选项）与添加订阅中可以选择下载器，留空跟随默认实例。只有一个下载器时不显示该选项。
- 新种子投递到规则选择的下载器；规则未选择时用订阅选择的，再退回默认实例。由订阅新建的规则继承订阅的选择。
- 每个种子记录它被添加到的下载器，之后的重命名、删除都在该下载器上进行。规则改用另一个下载器后，已有的种子留在原下载器的原位置，不会迁移。
- 重命名按下载器逐个进行。某个下载器连不上时跳过它，并在它第一次连不上时发送「下载器连接异常」通知，其它下载器照常处理。
- 下载器页与种子列表在有多个下载器时标出每个种子所在的下载器。
- 删除下载器后，选择它的规则与订阅改用默认实例，其中已有的种子不受影响。

## 常见问题

### 下载器地址

::: warning 注意
Docker Bridge 模式下，请勿把下载器地址写成 `127.0.0.1` 或 `localhost`，除非下载器和 AutoBangumi 在同一个网络命名空间中。
:::

如果 AB 在 Docker Bridge 模式下运行，`127.0.0.1` 会指向 AB 容器自身，而不是宿主机或另一个下载器容器。

- qBittorrent / aria2 也在 Docker 中运行：优先使用同一个 Docker 网络内的服务名，或使用 Docker 网关地址，例如 `172.17.0.1:8080`。
- 下载器运行在宿主机上：使用宿主机局域网 IP。
- AB 使用 Host 网络模式：可以使用 `127.0.0.1`。
- aria2 示例：`172.17.0.1:6800`，密码栏填写 RPC secret。

::: warning 注意
Macvlan 会隔离容器网络。如果没有额外的网桥配置，容器无法访问宿主机或其他容器。
:::

### 下载路径问题

AB 中的下载路径用于生成保存位置和后续整理路径。请填写**下载器视角下**的路径：

- Docker：如果下载器把媒体目录挂载为 `/downloads`，可填写 `/downloads/Bangumi`。
- Linux/macOS：例如 `/home/user/downloads/Bangumi`。
- Windows：例如 `D:\Media\Bangumi`。

## `config.json` 配置选项

下载器是 `plugins.instances` 中 `point` 为 `downloader` 的实例，`plugins.slots.downloader` 是默认实例的 id（默认为 `default`）。在设置页新建实例时，id 只能包含字母、数字、`_` 与 `-`：

```json
"plugins": {
    "slots": { "downloader": "default" },
    "instances": [
        {
            "id": "default",
            "point": "downloader",
            "provider": "qbittorrent",
            "options": { "host": "172.17.0.1:8080", "username": "admin", "password": "adminadmin", "path": "/downloads/Bangumi", "ssl": false }
        }
    ]
}
```

3.3 的 `downloader` 配置节在升级到 4.0 后第一次启动时自动迁移到 `default` 实例，原文件备份为 `config.json.v3.bak`。环境变量 `AB_DOWNLOADER_HOST`、`AB_DOWNLOADER_USERNAME`、`AB_DOWNLOADER_PASSWORD`、`AB_DOWNLOAD_PATH` 照常生效，写入默认实例。

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `provider` | 下载器类型 | 字符串 | 下载器类型 | `qbittorrent` |
| `host` | 下载器地址 | 字符串 | 下载器地址 | `172.17.0.1:8080` |
| `username` | 下载器用户名 | 字符串 | 用户名 | `admin` |
| `password` | 下载器密码或 aria2 RPC secret | 字符串 | 密码 | `adminadmin` |
| `path` | 下载路径 | 字符串 | 下载地址 | `/downloads/Bangumi` |
| `ssl` | 启用 HTTPS | 布尔值 | SSL | `false` |
