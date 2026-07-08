---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

title: AutoBangumi
titleTemplate: Fully automated anime tracking

hero:
  name: AutoBangumi
  text: Fully automated anime tracking
  tagline: Automated RSS subscription parsing, download management, and media organization
  actions:
    - theme: brand
      text: Quick Start
      link: /en/deploy/quick-start
    - theme: alt
      text: About
      link: /en/home/
    - theme: alt
      text: Changelog
      link: /en/changelog/3.3

features:
  - icon:
      src: /image/icons/rss.png
    title: RSS Subscription Parsing
    details: Automatically recognizes and parses anime RSS subscriptions. Subscribe once, then AutoBangumi handles parsing, downloading, and organization.
  - icon:
      src: /image/icons/qbittorrent-logo.svg
    title: qBittorrent / aria2 Downloaders
    details: Download anime with qBittorrent or aria2, manage existing series, fetch missed episodes, and remove entries from AutoBangumi.
  - icon:
      src: /image/icons/tmdb-icon.png
    title: TMDB Metadata Matching
    details: Match anime metadata through TMDB so titles remain accurate even across different subtitle groups and release names.
  - icon:
      src: /image/icons/plex-icon.png
    title: Plex / Jellyfin / Infuse ...
    details: Organize filenames and folders for media libraries, improving metadata scraping success in Plex, Jellyfin, Infuse, and similar apps.
---


<div class="container">
<div class="vp-doc">

## Acknowledgements

### Thanks
- [Mikan Project](https://mikanani.me) for excellent anime resources.
- [VitePress](https://vitepress.dev) for the documentation framework.
- [qBittorrent](https://www.qbittorrent.org) for the downloader.
- [aria2](https://aria2.github.io) for the downloader.
- [Plex](https://www.plex.tv) / [Jellyfin](https://jellyfin.org) for self-hosted media libraries.
- [Infuse](https://firecore.com/infuse) for an elegant video player.
- [DanDanPlay](https://www.dandanplay.com) for danmaku playback.
- Every anime production team, subtitle group, and fan.

### Contributors

[
  ![](https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi){class=contributors-avatar}
](https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors)

## Disclaimer

AutoBangumi obtains anime through unofficial copyright channels:

- **Do not** use AutoBangumi for commercial purposes.
- **Do not** create videos containing AutoBangumi and publish them on domestic video platforms related to copyright holders.
- **Do not** use AutoBangumi for any activity that violates laws or regulations.

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
