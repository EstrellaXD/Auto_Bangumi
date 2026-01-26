---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

title: AutoBangumi
titleTemplate: Automatic anime tracking, hands-free!

hero:
  name: AutoBangumi
  text: Automatic anime tracking, hands-free!
  tagline: Fully automated RSS subscription parsing, download management, and file organization
  actions:
    - theme: brand
      text: Quick Start
      link: /deploy/quick-start
    - theme: alt
      text: About
      link: /home/
    - theme: alt
      text: Changelog
      link: /changelog/3.2

features:
  - icon:
      src: /image/icons/rss.png
    title: RSS Subscription Parsing
    details: Automatically identifies and parses anime RSS feeds. No manual input needed — just subscribe and it handles parsing, downloading, and organizing.
  - icon:
      src: /image/icons/qbittorrent-logo.svg
    title: qBittorrent Downloader
    details: Uses qBittorrent to download anime resources. Manage existing anime, download older series, and delete entries all within AutoBangumi.
  - icon:
      src: /image/icons/tmdb-icon.png
    title: TMDB Metadata Matching
    details: Matches anime information via TMDB for accurate metadata, ensuring correct parsing even across multiple subtitle groups.
  - icon:
      src: /image/icons/plex-icon.png
    title: Plex / Jellyfin / Infuse ...
    details: Automatically organizes file names and directory structure based on match results, ensuring high success rates for media library metadata scraping.
---


<div class="container">
<div class="vp-doc">

## Credits

### Acknowledgments
Thanks to
- [Mikan Project](https://mikanani.me) for providing such a great anime resource.
- [VitePress](https://vitepress.dev) for providing a great documentation framework.
- [qBittorrent](https://www.qbittorrent.org) for providing a great downloader.
- [Plex](https://www.plex.tv) / [Jellyfin](https://jellyfin.org) for providing great self-hosted media libraries.
- [Infuse](https://firecore.com/infuse) for providing an elegant video player.
- [DanDan Play](https://www.dandanplay.com) for providing a great danmaku player.
- Every anime production team / translator team / fans.

### Contributors

[
  ![](https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi){class=contributors-avatar}
](https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors)

## Disclaimer

Since AutoBangumi obtains anime through unofficial copyright channels:

- **Do not** use AutoBangumi for commercial purposes.
- **Do not** create video content featuring AutoBangumi for distribution on domestic video platforms (copyright stakeholders).
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
