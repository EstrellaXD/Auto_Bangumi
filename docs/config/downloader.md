# 下载器设置

## WebUI 设置

![downloader](../image/config/downloader.png){width=500}{class=ab-shadow-card}

<br/>

- **Downloader Type** 为下载器类型，目前支持 qBittorrent 下载器，目前暂不支持修改。
- **Host** 为下载器地址。[1](#下载器地址)
- **Download path** 为映射的下载器下载路径。[2](#下载器路径问题)
- **SSL** 为下载器是否使用 SSL。

## 常见问题

### 下载器地址

::: warning 注意
请不要直接使用 127.0.0.1 或 localhost 作为下载器地址。
:::

由于 AB 在官方教程中是以 **Bridge** 模式运行在 Docker 中的，如果你是用 127.0.0.1 或者 localhost 那么 AB 将会把这个地址解析为自身，而非下载器。
- 如果此时你的 qBittorrent 也运行在 Docker 中，那么我们推荐你是用 Docker 的 **网关地址：172.17.0.1**。
- 如果你的 qBittorrent 运行在宿主机上，那么你需要使用宿主机的 IP 地址。

如果你以 **Host** 模式运行 AB，那么你可以直接使用 127.0.0.1 代替 Docker 网关地址。

::: warning 注意
Macvlan 会隔离容器的网络，此时如果你不做额外的网桥配置将无法访问同宿主机的其他容器或者主机本身。
:::

### 下载器路径问题

AB 中配置的路径只是为了生成对应番剧文件路径，AB 本身不对路径下的文件做直接管理。

**下载路径** 到底写什么？

这个参数只要和你 **下载器** 中的参数保持一致即可。
- Docker：比如 qB 中是 `/downloads` 那就写 `/downloads/Bangumi`，`Bangumi`可以任意更改。
- Linux/macOS：如果是 `/home/usr/downloads` 或者 `/User/UserName/Downloads` 只要在最后再加一行 `Bangumi` 就行。
- Windows：`D:\Media\`, 改为 `D:\Media\Bangumi`

## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`downloader`

| 参数名      | 参数说明        | 参数类型 | WebUI 对应选项  | 默认值                |
|----------|-------------|------|-------------|--------------------|
| type     | 下载器类型       | 字符串  | 下载器类型       | qbittorrent        |
| host     | 下载器地址       | 字符串  | 下载器地址       | 172.17.0.1:8080    |
| username | 下载器用户名      | 字符串  | 下载器用户名      | admin              |
| password | 下载器密码       | 字符串  | 下载器密码       | adminadmin         |
| path     | 下载器下载路径     | 字符串  | 下载器下载路径     | /downloads/Bangumi |
| ssl      | 下载器是否使用 SSL | 布尔值  | 下载器是否使用 SSL | false              |



