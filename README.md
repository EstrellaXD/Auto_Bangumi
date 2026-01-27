<p align="center">
    <img src="docs/public/image/icons/light-icon.svg#gh-light-mode-only" width=50%/ alt="">
    <img src="docs/public/image/icons/dark-icon.svg#gh-dark-mode-only" width=50%/ alt="">
</p>
<p align="center">
    <img title="docker build version" src="https://img.shields.io/docker/v/estrellaxd/auto_bangumi" alt="">
    <img title="release date" src="https://img.shields.io/github/release-date/estrellaxd/auto_bangumi" alt="">
    <img title="docker pull" src="https://img.shields.io/docker/pulls/estrellaxd/auto_bangumi" alt="">
    <img title="python version" src="https://img.shields.io/badge/python-3.11-blue" alt="">
</p>

<p align="center">
  <a href="https://www.autobangumi.org">官方网站</a> | <a href="https://www.autobangumi.org/deploy/quick-start.html">快速开始</a> | <a href="https://www.autobangumi.org/changelog/3.2.html">更新日志</a> | <a href="https://t.me/autobangumi_update">更新推送</a> | <a href="https://t.me/autobangumi">TG 群组</a>
</p>

# 项目说明

<p align="center">
    <img title="AutoBangumi" src="docs/public/image/feature/bangumi-list.png" alt="" width=75%>
</p>

本项目是基于 RSS 的全自动追番整理下载工具。只需要在 [Mikan Project][mikan] 等网站上订阅番剧，就可以全自动追番。
并且整理完成的名称和目录可以直接被 [Plex][plex]、[Jellyfin][plex] 等媒体库软件识别，无需二次刮削。

## AutoBangumi 功能说明

### 核心功能

- 简易单次配置就能持续使用
- 无需介入的 `RSS` 解析器，解析番组信息并且自动生成下载规则
- 首次运行设置向导，7 步引导完成配置
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
- 支持多种 RSS 站点，支持聚合 RSS 的解析
- 无需维护完全无感使用
- 内置 TMDB 解析器，可以直接生成完整的 TMDB 格式的文件以及番剧信息

### 3.2 新功能

- **日历视图**：按播出日期查看订阅番剧，集成 Bangumi.tv 放送时间表
- **Passkey 无密码登录**：支持 WebAuthn 指纹/面容登录，支持无用户名登录
- **季度/集数偏移自动检测**：自动识别「虚拟季度」并计算正确的集数偏移
- **番剧归档**：手动或自动归档已完结番剧，保持列表整洁
- **搜索源设置面板**：在 UI 中直接管理搜索源，无需编辑配置文件
- **RSS 连接状态**：实时显示订阅源健康状态，快速定位问题
- **iOS 风格通知徽章**：直观显示需要关注的订阅
- **全新 UI 设计**：深色/浅色主题、移动端适配、毛玻璃登录页
- **性能优化**：并发 RSS 刷新提速 10 倍、并发下载提速 5 倍

## [Roadmap](https://github.com/users/EstrellaXD/projects/2)

***已支持的下载器：***

- qBittorrent
- Aria2
- Transmission

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=EstrellaXD/Auto_Bangumi&type=Date)](https://star-history.com/#EstrellaXD/Auto_Bangumi)

## 贡献

欢迎提供 ISSUE 或者 PR, 贡献代码前建议阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

贡献者名单请见：

<a href="https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors"><img src="https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi"></a>


## Licence

[MIT licence](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/LICENSE)

[mikan]: https://mikanani.me
[plex]: https://plex.tv
[jellyfin]: https://jellyfin.org
