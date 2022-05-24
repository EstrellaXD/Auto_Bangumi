<p align="center">
    <img src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/image/auto_bangumi_v2.png#gh-light-mode-only" width=50%/>
    <img src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/image/auto_bangumi_icon_v2-dark.png#gh-dark-mode-only" width=50%/>
</p>
<p align="center">
    <img title="mikan project" src="https://mikanani.me/images/mikan-pic.png" alt="" width="10%">
    <img title="qbittorrent" src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/New_qBittorrent_Logo.svg/600px-New_qBittorrent_Logo.svg.png" width="10%">
</p>
<p align="center">
    <img title="docker build version" src="https://img.shields.io/docker/v/estrellaxd/auto_bangumi" alt="">
    <img title="release date" src="https://img.shields.io/github/release-date/estrellaxd/auto_bangumi" alt="">
    <img title="docker pull" src="https://img.shields.io/docker/pulls/estrellaxd/auto_bangumi" alt="">
</p>


# 项目说明

本项目是基于 [Mikan Project](https://mikanani.me)、[qBittorrent](https://qbittorrent.org) 的全自动追番整理下载工具。只需要在 [Mikan Project](https://mikanani.me) 上订阅番剧，就可以全自动追番。并且整理完成的名称和目录可以直接被 [Plex]()、[Jellyfin]() 等媒体库软件识别，无需二次刮削。

基于 [infuse]() 与 [Plex]() 的效果如下：

<img title="plex" src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/image/截屏2022-05-23%2020.47.39.png" alt="" width=50%><img title="infuse" src="https://github.com/EstrellaXD/Auto_Bangumi/blob/main/image/截屏2022-05-23%2020.48.02.png" alt="" width=50%>

## 相关文档和群组

- [AutoBangumi V2 简易说明](https://www.craft.do/s/4viN6M3tBqigLp)
- 更新推送：[Telegram Channel](https://t.me/autobangumi_update)
- Bug 反馈群：[Telegram](t.me/autobangumi)

# 部署说明
1. 安装 qBittorrent:
    
2. 用 Docker 部署 `AutoBangumi` :

```other
docker run -d \
	--name=AutoBangumi \
	-e TZ=Asia/Shanghai \ #optional
	-e TIME=1800 \ #optional
	-e HOST=localhost:8080 \ #optional
	-e USER=admin \ #optional
	-e PASSWORD=adminadmin \ #optional
	-e METHOD=pn \ #optional
	-e GROUP=True \ #optional
	-e DOWNLOAD_PATH=/path/downloads \
	-e RSS=<YOUR RSS ADDRESS> \
	--network=host \
	--restart unless-stopped \
 	estrellaxd/auto_bangumi:latest
```
### 参数说明

| 环境变量            | 作用                  | 参数               |
| --------------- | ------------------- | ---------------- |
| `TZ`            | 时区                  | `Asia/Shanghai`  |
| `TIME`          | 间隔时间                | `1800`           |
| `HOST`          | qBittorrent 的地址和端口号 | `localhost:8080` |
| `USER`          | qBittorrent 的用户名    | `admin`          |
| `PASSWORD`      | qBittorrent 的密码     | `adminadmin`     |
| `METHOD`        | 重命名方法               | `pn`             |
| `GROUP_TAG`     | 是否在下载规则中添加组名        | `False`          |
| `DOWNLOAD_PATH` | qBittorrent 中的下载路径  | 必填项              |
| `RSS`           | RSS 订阅地址            | 必填项              |

- `TIME` : 程序运行的间隔时间，默认为 `1800` 也就是 30 分钟，如果更新时间要求比较高可以适当降低该值。
- `HOST`, `USER`, `PASSWORD`: qBittorrent 的地址，用户名，密码。
- `METHOD`: 重命名规则
  - `pn`: Pure Name 模式，去掉所有字幕组以及番剧额外信息，只保留名称、季度和集数。
  - `normal`: 正常模式，仅重命名会影响搜刮的非正常字符。
- `GROUP_TAG`: 开启后自动在自动下载规则中创建组名，方便管理。
- `DOWNLOAD_PATH`: qBittorrent 的下载地址。
- `RSS`: Mikan Project 的个人 RSS 订阅链接

3. 检查 Docker 运行日志，出现：

```other
[2022-05-20 12:47:47]  RSS Already exists.
[2022-05-20 12:47:47]  add Summer Time Rendering 
[2022-05-20 12:47:47]  add Paripi Koumei 
[2022-05-20 12:47:47]  add Tomodachi Game 
[2022-05-20 12:47:47]  add Tate no Yuusha no Nariagari S02
[2022-05-20 12:47:47]  add Shijou Saikyou no Daimaou 
[2022-05-20 12:47:47]  add Yuusha, Yamemasu 
[2022-05-20 12:47:47]  add Aharen-san wa Hakarenai 
[2022-05-20 12:47:47]  add Kawaii dake ja Nai Shikimori-san 
[2022-05-20 12:47:47]  add Kakkou no Iinazuke 
[2022-05-20 12:47:47]  add SPYxFAMILY 
[2022-05-20 12:47:47]  add Love Live S02
[2022-05-20 12:47:47]  add BUILD-DIVIDE 
[2022-05-20 12:47:47]  add Machikado Mazoku:-choume 
[2022-05-20 12:47:47]  add CUE! 
[2022-05-20 12:47:47]  add Kaguya-sama wa Kokurasetai S03
[2022-05-20 12:47:47]  add Shokei Shoujo no Virgin Road 
[2022-05-20 12:47:47]  add Kakkou no Iikagen 
[2022-05-20 12:47:47]  Start adding rules.
[2022-05-20 12:47:47]  Finished.
[2022-05-20 12:47:47]  已完成对0个文件的检查
[2022-05-20 12:47:47]  已对其中0个文件进行重命名
[2022-05-20 12:47:47]  完成
```

说明运行成功。之后可以检查 qb 中是否建立自动下载规则。

4. 安装媒体库软件

# 声明
本项目的自动改名规则根据 [miracleyoo/anime_renamer](https://github.com/miracleyoo/anime_renamer) 项目
