## 使用 Docker-cli 部署

### 设置环境变量

添加环境变量（注意这里最好手动输入）详细内容请参考 [Docker Compose](/deploy/Docker-compose) 章节中同样内容

```shell
export \
DOWNLOAD_PATH=/path/downloads \
RSS=<RSS_LINK>
```

### 创建数据和配置文件夹

为了保证 AB 在每次更新之后数据和配置不丢失，推荐使用 Docker volume 进行数据和配置的持久化。

```shell
# 创建数据文件夹
mkdir AutoBangumi
cd AutoBangumi
```

### 使用 Docker-cli 部署 AutoBangumi

复制以下命令运行即可。

```shell
docker run -d \
  --name=AutoBangumi \
  -v $PWD/config:/app/config \
  -v $PWD/data:/app/data \
  -p 7892:7892 \
  --network=bridge \
  --dns=8.8.8.8 \
  --restart unless-stopped \
  estrellaxd/auto_bangumi:latest
```

此时 AB 的 WebUI 会自动运行，但是主程序会处于暂停状态，可以进入 `http://abhost:7892` 进行配置。

当然也可以使用环境变量进行配置，具体内容请参考 [Docker Compose](/deploy/Docker-compose) 章节中同样内容

```shell
docker run -d \
  --name=AutoBangumi \
  -e TZ=Asia/Shanghai \ #optional
  -e AB_DOWNLOADER_HOST=qbittorrent:8080 \ #optional
  -e AB_DOWNLOADER_USERNAME=admin \ #optional
  -e AB_DOWNLOADER_PASSWORD=adminadmin \ #optional
  -e AB_DOWNLOAD_PATH=/path/downloads \
  -e AB_RSS=<YOUR_RSS_ADDRESS> \
  -v $PWD/config:/app/config \
  -v $PWD/data:/app/data \
  --network=host \
  --dns=8.8.8.8 \
  --restart unless-stopped \
  estrellaxd/auto_bangumi:latest
```

此时 AB 会自动把环境变量写入 `config.json` 文件中然后自动运行。

推荐使用 _[Portainer](https://www.portainer.io)_ 等带有 UI 的 Docker 管理器进行进阶部署

## 部署结果：

```other
[2022-07-09 21:55:19,164] INFO:	                _        ____                                    _
[2022-07-09 21:55:19,165] INFO:	     /\        | |      |  _ \                                  (_)
[2022-07-09 21:55:19,166] INFO:	    /  \  _   _| |_ ___ | |_) | __ _ _ __   __ _ _   _ _ __ ___  _
[2022-07-09 21:55:19,167] INFO:	   / /\ \| | | | __/ _ \|  _ < / _` | '_ \ / _` | | | | '_ ` _ \| |
[2022-07-09 21:55:19,167] INFO:	  / ____ \ |_| | || (_) | |_) | (_| | | | | (_| | |_| | | | | | | |
[2022-07-09 21:55:19,168] INFO:	 /_/    \_\__,_|\__\___/|____/ \__,_|_| |_|\__, |\__,_|_| |_| |_|_|
[2022-07-09 21:55:19,169] INFO:	                                            __/ |
[2022-07-09 21:55:19,169] INFO:	                                           |___/
[2022-07-09 21:55:19,170] INFO:	Version 2.6.3  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan
[2022-07-09 21:55:19,171] INFO:	GitHub: https://github.com/EstrellaXD/Auto_Bangumi/
[2022-07-09 21:55:19,172] INFO:	Starting AutoBangumi...
[2022-07-09 21:55:20,717] INFO:	Add RSS Feed successfully.
[2022-07-09 21:55:21,761] INFO:	Start collecting RSS info.
[2022-07-09 21:55:23,431] INFO:	Finished
[2022-07-09 21:55:23,432] INFO:	Running....
[2022-07-09 22:01:24,534] INFO:	[NC-Raws] 继母的拖油瓶是我的前女友 - 01 (B-Global 1920x1080 HEVC AAC MKV) [0B604F3A].mkv >> 继母的拖油瓶是我的前女友 S01E01.mkv
[2022-07-09 22:01:24,539] INFO:	Finished checking 131 files' name, renamed 1 files.
[2022-07-09 23:55:31,843] INFO:	Start collecting RSS info.
[2022-07-09 23:55:37,269] INFO:	Finished
[2022-07-09 23:55:37,270] INFO:	Running....
[2022-07-10 00:13:38,855] INFO:	[NC-Raws] Lycoris Recoil 莉可麗絲 - 02 (Baha 1920x1080 AVC AAC MP4) [1160E633].mp4 >> Lycoris Recoil 莉可麗絲 S01E02.mp4
[2022-07-10 00:13:38,869] INFO:	Finished checking 131 files' name, renamed 1 files.
[2022-07-10 00:43:40,777] INFO:	[NC-Raws] Lycoris Recoil 莉可麗絲 - 01 (Baha 1920x1080 AVC AAC MP4) [7E742084].mp4 >> Lycoris Recoil 莉可麗絲 S01E01.mp4
[2022-07-10 00:43:40,811] INFO:	Finished checking 132 files' name, renamed 1 files.
```
