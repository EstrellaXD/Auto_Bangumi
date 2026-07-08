# 播放器设置

播放器设置用于侧边栏中的 **播放器** 页面，方便在 WebUI 内跳转或嵌入媒体服务器。

![player](/image/config/player.png){width=700}{class=ab-shadow-card}

- **类型**：
  - `jump`：打开播放器页面时跳转到外部媒体服务器。
  - `iframe`：在 AB 页面内嵌入媒体服务器。
- **播放器地址**：Jellyfin、Emby、Plex 等服务的访问地址。未填写协议时，前端会自动补 `http://`。

::: tip
播放器设置保存在浏览器本地存储中，不属于 `config.json`，也不需要点击底部 **保存并重启**。
:::
