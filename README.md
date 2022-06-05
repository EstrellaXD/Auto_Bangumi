<p align="center">
    <img src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/docs/image/auto_bangumi_v2.png#gh-light-mode-only" width=50%/>
    <img src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/docs/image/auto_bangumi_icon_v2-dark.png#gh-dark-mode-only" width=50%/>
</p>
<p align="center">
    <img title="docker build version" src="https://img.shields.io/docker/v/estrellaxd/auto_bangumi" alt="">
    <img title="release date" src="https://img.shields.io/github/release-date/estrellaxd/auto_bangumi" alt="">
    <img title="docker pull" src="https://img.shields.io/docker/pulls/estrellaxd/auto_bangumi" alt="">
    <img title="python version" src="https://img.shields.io/badge/python-3.10-blue" alt="">
    <img title="platform arch" src="https://img.shields.io/badge/arch-%20AMD64%20%2F%20ARM64-lightgrey" alt="">
</p>

# 项目说明

<p align="center">
    <img title="mikan project" src="https://mikanani.me/images/mikan-pic.png" alt="" width="10%">
    <img title="qbittorrent" src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/New_qBittorrent_Logo.svg/600px-New_qBittorrent_Logo.svg.png" width="10%">
</p>

本项目是基于 [Mikan Project](https://mikanani.me)、[qBittorrent](https://qbittorrent.org) 的全自动追番整理下载工具。只需要在 [Mikan Project](https://mikanani.me) 上订阅番剧，就可以全自动追番。并且整理完成的名称和目录可以直接被 [Plex]()、[Jellyfin]() 等媒体库软件识别，无需二次刮削。

基于 [infuse](https://firecore.com/infuse) 与 [Plex](https://plex.tv) 的效果如下：

<img title="plex" src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/docs/image/截屏2022-05-23%2020.47.39.png" alt="" width=50%><img title="infuse" src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/docs/image/截屏2022-05-23%2020.48.02.png" alt="" width=50%>

## [部署说明](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/docs/部署说明.md) / [常见错误说明](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/docs/常见错误解决.md)

## AutoBangumi 功能说明

- 简易单词配置就能持续使用
- 无需介入的 `RSS` 解析器，解析番组信息并且自动生成下载规则。
- 番剧文件整理:
    ```
    downloader
    ├── bangumi_A_title
    │   ├── SO1
    │   │   ├── A E01.mp4
    │   │   ├── A E02.mp4
    │   │   ├── A E03.mp4
    │   │   └── A E04.mp4
    │   └── SO2
    │       ├── A E01.mp4
    │       ├── A E02.mp4
    │       ├── A E03.mp4
    │       └── A E04.mp4
    ```
- 全自动重命名，重命名后 95% 以上的番剧可以直接被媒体库软件直接刮削
    ```
  [Lilith-Raws] Kakkou no Iinazuke - 07 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4 
  >>
   Kakkou no Iinazuke E07.mp4
  ```
- 季中追番可以补全当季遗漏的所有剧集
- 无需维护完全无感的使用体验

## 相关群组

- 更新推送：[Telegram Channel](https://t.me/autobangumi_update)
- Bug 反馈群：[Telegram](https://t.me/+yNisOnDGaX5jMTM9)

## Roadmap

***开发中的功能：***

- ✅ RSS 解析器：AutoBangumi 可以自行解析分析种子无需依赖下载器。
- Transmission & Aria2 的支持。
- ✅ 遗漏番剧下载：中间开始追番可以补全之前的剧集。

***计划开发的功能：***

- Web UI
- 更为智能细致的分类预设。

# 声明
感谢 [Sean](https://github.com/findix) 提供的大量帮助

## Licence
[MIT licence](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/LICENSE)


