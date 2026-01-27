---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

title: AutoBangumi
titleTemplate: 全自动追番，解放双手！

hero:
  name: AutoBangumi
  text: 全自动追番，解放双手！
  tagline: 全自动 RSS 订阅解析、下载管理和文件整理
  actions:
    - theme: brand
      text: 快速开始
      link: /deploy/quick-start
    - theme: alt
      text: 关于
      link: /home/
    - theme: alt
      text: 更新日志
      link: /changelog/3.2

features:
  - icon:
      src: /image/icons/rss.png
    title: RSS 订阅解析
    details: 自动识别并解析番剧 RSS 订阅源。无需手动输入，只需订阅即可自动完成解析、下载和整理。
  - icon:
      src: /image/icons/qbittorrent-logo.svg
    title: qBittorrent 下载器
    details: 使用 qBittorrent 下载番剧资源。在 AutoBangumi 中即可管理现有番剧、下载往期番剧以及删除条目。
  - icon:
      src: /image/icons/tmdb-icon.png
    title: TMDB 元数据匹配
    details: 通过 TMDB 匹配番剧信息以获取准确的元数据，确保即使在多个字幕组之间也能正确解析。
  - icon:
      src: /image/icons/plex-icon.png
    title: Plex / Jellyfin / Infuse ...
    details: 根据匹配结果自动整理文件名和目录结构，确保媒体库软件能够高成功率地刮削元数据。
---


<div class="container">
<div class="vp-doc">

## 鸣谢

### 致谢
感谢
- [Mikan Project](https://mikanani.me) 提供了如此优秀的番剧资源。
- [VitePress](https://vitepress.dev) 提供了优秀的文档框架。
- [qBittorrent](https://www.qbittorrent.org) 提供了优秀的下载器。
- [Plex](https://www.plex.tv) / [Jellyfin](https://jellyfin.org) 提供了优秀的自托管媒体库。
- [Infuse](https://firecore.com/infuse) 提供了优雅的视频播放器。
- [弹弹 Play](https://www.dandanplay.com) 提供了优秀的弹幕播放器。
- 每一个番剧制作组 / 字幕组 / 爱好者。

### 贡献者

[
  ![](https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi){class=contributors-avatar}
](https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors)

## 免责声明

由于 AutoBangumi 通过非官方版权渠道获取番剧：

- **请勿**将 AutoBangumi 用于商业用途。
- **请勿**制作包含 AutoBangumi 的视频内容并在国内视频平台（版权相关方）上发布。
- **请勿**将 AutoBangumi 用于任何违反法律法规的活动。

</div>
</div>

<style scoped>
.container {
  display: flex;
  position: relative;
  margin: 0 auto;
  padding: 0 24px;
  max-width: 1280px;
}

@media (min-width: 640px) {
  .container {
    padding-inline: 48px;
  }
}

@media (min-width: 960px) {
  .container {
    padding-inline: 64px;
  }
}


.contributors-avatar {
  width: 600px;
}
</style>
