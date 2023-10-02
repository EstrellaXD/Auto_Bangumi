---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

title: AutoBangumi
titleTemplate: 自动追番，解放双手！

hero:
  name: AutoBangumi
  text: 自动追番，解放双手！
  tagline: 从 RSS 全自动 订阅解析、下载管理、重命名整理
#  image:
#    dark: /image/icons/dark-logo.svg
#    light: /image/icons/light-logo.svg
#    alt: AutoBangumi WebUI
  actions:
    - theme: brand
      text: 快速开始
      link: /deploy/quick-start
    - theme: alt
      text: 项目说明
      link: /home/
    - theme: alt
      text: 更新日志
      link: /changelog/3.0

features:
  - icon:
      src: /image/icons/rss.png
    title: RSS 订阅解析
    details: 自动识别解析各种番剧 RSS，无需手动输入番剧，仅需订阅即可自动解析、下载、整理。
  - icon:
      src: /image/icons/qbittorrent-logo.svg
    title: qBitTorrent 下载器
    details: 使用 qBitTorrent 共享下载番剧资源，在 AutoBangumi 中可管理已有番剧、下载旧番、删除番剧。
  - icon:
      src: /image/icons/tmdb-icon.png
    title: The Movie DB 解析匹配
    details: 可根据 TMDB 最大程度匹配对应番剧信息，保证对多个字幕组的资源也能正确匹配与解析。
  - icon:
      src: /image/icons/plex-icon.png
    title: Plex / Jellyfin / Infuse ...
    details: 根据番剧匹配结果自动整理资源文件名，统一目录结构，保证各类媒体库元信息刮削成功率。
---


<div class="container">
<div class="vp-doc">

## 致谢声明

### Credits
Thanks to 
- [Mikan Project](https://mikanani.me) for providing the so great anime resource.
- [VitePress](https://vitepress.dev) for providing a great documentation framework.
- [qBitTorrent](https://www.qbittorrent.org) for providing a great downloader.
- [Plex](https://www.plex.tv) / [Jellyfin](https://jellyfin.org) for providing some great self-host media libraries.
- [Infuse](https://firecore.com/infuse) for providing an elegant video player.
- [DanDan Play](https://www.dandanplay.com) for providing a great danmaku player.
- Every bangumi production team / translator team / fans.

### Contributors

[
  ![](https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi){class=contributors-avatar}
](https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors)

## 传播声明

由于 AutoBangumi 为非正规版权渠道获取番剧，因此：

- **请勿**将 AutoBangumi 用于商业用途。
- **请勿**将 AutoBangumi 制作为视频内容，于境内视频网站(版权利益方)传播。
- **请勿**将 AutoBangumi 用于任何违反法律法规的行为。

</div>
</div>

<style scoped>
.container {
  display: flex;
  position: relative;
  margin: 0 auto;
  padding: 0 24px;
  /**
   * same as VPHero.vue
   * https://github.com/vuejs/vitepress/blob/v1.0.0-beta.5/src/client/theme-default/components/VPHero.vue#L83
   */
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



