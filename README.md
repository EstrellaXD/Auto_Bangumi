# AutoBangumi - 全自动追番程序
# 2.0
2.0 Stable 已经完成，相比于 1.0 改进：
- 无需手动设定下载规则
- 更符合刮削器的命名规则
- 自动归类 Season

<img src="https://github.com/EstrellaXD/Bangumi_Auto_Collector/blob/main/image/workthrough-1.0.png?raw=true" alt="drawing" width="345.15"/><img src="https://github.com/EstrellaXD/Bangumi_Auto_Collector/blob/main/image/workthrough-2.0.png?raw=true" alt="drawing" width="350"/>

- [AutoBangumi V2 简易说明](https://www.craft.do/s/4viN6M3tBqigLp)
- 更新推送：[Telegram Channel](https://t.me/autobangumi_update)
- 测试群：[Telegram](t.me/autobangumi)

## 部署说明

1. 用 Docker 部署 `AutoBangumi` ：

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

1. 检查 Docker 运行日志，出现：

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
# V 1.0
本版本只能作为番剧重命名方便刮削
## 说明
本项目根据 qBittorrent, Plex 以及 infuse 搭建
![Image](https://cdn.sspai.com/2022/02/09/d94ec60db1c136f6b12ba3dca31e5f5f.png?imageView2/2/w/1120/q/90/interlace/1/ignore-error/1)
完整教程请移步 [自动追番机器建立教程](https://www.craft.do/s/48MFW9QwaCQMzt)
### 需要依赖
```bash
pip install qbittorrent-api
```
## 使用之前
在 `config.json` 中填入你的 `hostip` `username` `password` `savepath`:
```json
{
  "host_ip": "192.168.31.10:8181",
  "username": "admin",
  "password": "adminadmin",
  "savepath": "/downloads/Bangumi",
  "method": "pn"
}
```
## 自动下载规则建立
```shell
python3 rule_set.py --name <新番名称>
```
## rename_qb
```shell
python3 rename_qb.py --help
```
目前有三种重命名模式
- `normal`: 普通模式，直接重命名，保留番剧字幕组信息。
- `pn`: 纯净模式，保留番剧名称和剧集信息，去掉多余信息。

然后运行 `rename_qb.py` 即可, 如果只想对新番进行重命名，可以在程序中添加添加 `categories="Bangumi"` 语句

根据 `qBittorrent` API 自动重命名下载的种子文件，且不会让种子失效。

- 可以作为 `bash` 脚本运行，可以直接使用仓库中的 `rename.sh`
- 可以构建 `crontab` 定时运行
- 可以使用 Docker 部署，详见文末（推荐）
```shell
0,30 * * * * python3 /path/rename_qb.py
```
- 也可以监测文件夹变化运行。

## Docker 部署
可以使用 Docker 部署重命名应用：
```shell
docker run -d \
  --name=Bangumi_rename \
  -e HOST=192.168.31.10:8181 \
  -e USER=admin \
  -e PASSWORD=adminadmin \
  -e METHOD=pn \
  -e TIME=1800 \
  estrellaxd/bangumi_rename_qb:latest
```
`TIME` 为间隔运行时间，单位为秒
# 声明
本项目的自动改名规则根据 [miracleyoo/anime_renamer](https://github.com/miracleyoo/anime_renamer) 项目
