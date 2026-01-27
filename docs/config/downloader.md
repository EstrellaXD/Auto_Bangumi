# 下载器设置

## WebUI 配置

![downloader](/image/config/downloader.png){width=500}{class=ab-shadow-card}

<br/>

- **下载器类型** 为下载器类型。目前仅支持 qBittorrent。
- **地址** 为下载器地址。[详见下方说明](#下载器地址)
- **下载路径** 为下载器的映射下载路径。[详见下方说明](#下载路径问题)
- **SSL** 启用下载器连接的 SSL。

## 常见问题

### 下载器地址

::: warning 注意
请勿使用 127.0.0.1 或 localhost 作为下载器地址。
:::

由于官方教程中 AB 在 Docker 的 **Bridge** 模式下运行，使用 127.0.0.1 或 localhost 会解析到 AB 自身，而非下载器。
- 如果 qBittorrent 也在 Docker 中运行，建议使用 Docker **网关地址：172.17.0.1**。
- 如果 qBittorrent 运行在宿主机上，请使用宿主机的 IP 地址。

如果 AB 以 **Host** 模式运行，则可以使用 127.0.0.1 代替 Docker 网关地址。

::: warning 注意
Macvlan 会隔离容器网络。如果没有额外的网桥配置，容器无法访问其他容器或宿主机本身。
:::

### 下载路径问题

AB 中配置的路径仅用于生成对应的番剧文件路径。AB 本身不会直接管理该路径下的文件。

**下载路径应该填什么？**

此参数只需与**下载器**的配置匹配：
- Docker：如果 qB 使用 `/downloads`，则设置为 `/downloads/Bangumi`。`Bangumi` 可以改为任意名称。
- Linux/macOS：如果是 `/home/usr/downloads` 或 `/User/UserName/Downloads`，只需在末尾添加 `/Bangumi`。
- Windows：将 `D:\Media\` 改为 `D:\Media\Bangumi`

## `config.json` 配置选项

配置文件中的对应选项如下：

配置节：`downloader`

| 参数     | 说明         | 类型    | WebUI 选项      | 默认值              |
|----------|--------------|---------|-----------------|---------------------|
| type     | 下载器类型   | 字符串  | 下载器类型      | qbittorrent         |
| host     | 下载器地址   | 字符串  | 下载器地址      | 172.17.0.1:8080     |
| username | 下载器用户名 | 字符串  | 下载器用户名    | admin               |
| password | 下载器密码   | 字符串  | 下载器密码      | adminadmin          |
| path     | 下载路径     | 字符串  | 下载路径        | /downloads/Bangumi  |
| ssl      | 启用 SSL     | 布尔值  | 启用 SSL        | false               |
