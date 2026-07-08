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

配置节：`downloader`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `type` | 下载器类型 | 字符串 | 下载器类型 | `qbittorrent` |
| `host` | 下载器地址 | 字符串 | 下载器地址 | `172.17.0.1:8080` |
| `username` | 下载器用户名 | 字符串 | 用户名 | `admin` |
| `password` | 下载器密码或 aria2 RPC secret | 字符串 | 密码 | `adminadmin` |
| `path` | 下载路径 | 字符串 | 下载地址 | `/downloads/Bangumi` |
| `ssl` | 启用 HTTPS | 布尔值 | SSL | `false` |
