---
title: 项目说明
---

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../image/icons/dark-icon.svg">
  <source media="(prefers-color-scheme: light)" srcset="../image/icons/light-icon.svg">
  <img src="../image/icons/light-icon.svg" width=50%>
</picture>
</p>


## 项目说明


<p align="center">
  <img
    title="AutoBangumi WebUI"
    alt="AutoBangumi WebUI"
    src="../image/preview/window.png"
    width=85%
    data-zoomable
  >
</p>

**`AutoBangumi`** 是基于 RSS 的全自动追番整理下载工具。只需要在 [Mikan Project][mikan] 等网站上订阅番剧，就可以全自动追番。
并且整理完成的名称和目录可以直接被 [Plex][plex]、[Jellyfin][jellyfin] 等媒体库软件识别，无需二次刮削。

## 功能说明

- 简易单次配置就能持续使用
- 无需介入的 `RSS` 解析器，解析番组信息并且自动生成下载规则。
- 番剧文件整理:

  ```
  Bangumi
  ├── bangumi_A_title
  │   ├── Season 1
  │   │   ├── A S01E01.mp4
  │   │   ├── A S01E02.mp4
  │   │   ├── A S01E03.mp4
  │   │   └── A S01E04.mp4
  │   └── Season 2
  │       ├── A S02E01.mp4
  │       ├── A S02E02.mp4
  │       ├── A S02E03.mp4
  │       └── A S02E04.mp4
  ├── bangumi_B_title
  │   └─── Season 1
  ```

- 全自动重命名，重命名后 99% 以上的番剧可以直接被媒体库软件直接刮削

  ```
  [Lilith-Raws] Kakkou no Iinazuke - 07 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4
  >>
  Kakkou no Iinazuke S01E07.mp4
  ```

- 自定义重命名，可以根据上级文件夹对所有子文件重命名。
- 季中追番可以补全当季遗漏的所有剧集
- 高度可自定义的功能选项，可以针对不同媒体库软件微调
- 无需维护完全无感使用
- 内置 TMDB 解析器，可以直接生成完整的 TMDB 格式的文件以及番剧信息。
- 对于 Mikan RSS 的反代支持。

## 相关群组

- 更新推送：[Telegram Channel](https://t.me/autobangumi_update)
- Bug 反馈群：[Telegram](https://t.me/+yNisOnDGaX5jMTM9)

## 致谢

感谢 [Sean](https://github.com/findix) 提供的大量帮助

## 贡献

欢迎提供 ISSUE 或者 PR

<a href="https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi" />
</a>

## 传播声明

由于 AutoBangumi 为非正规版权渠道获取番剧，因此：

- **请勿**将 AutoBangumi 用于商业用途。
- **请勿**将 AutoBangumi 制作为视频内容，于境内视频网站(版权利益方)传播。
- **请勿**将 AutoBangumi 用于任何违反法律法规的行为。


AutoBangumi 仅供学习交流使用。

## Licence

[MIT licence](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/LICENSE)

[mikan]: https://mikanani.me
[plex]: https://plex.tv
[jellyfin]: https://jellyfin.org

