# 快速开始

我们推荐你在 Docker 中部署运行 AutoBangumi。
部署前请确认已经安装了 [Docker Engine][docker-engine] 或者 [Docker Desktop][docker-desktop]。

## 创建数据和配置文件夹

为了保证 AB 在每次更新之后数据和配置不丢失，推荐使用 Docker volume 进行数据和配置的持久化。

```shell
docker volume create AutoBangumi_config
docker volume create AutoBangumi_data
```
## 使用 Docker 部署 AutoBangumi

### 选项1: 使用 Docker-cli 部署

复制以下命令运行即可。

```shell
docker run -d \
  --name=AutoBangumi \
  -v AutoBangumi_config:/app/config \
  -v AutoBangumi_data:/app/data \
  -p 7892:7892 \
  --network=bridge \
  --dns=8.8.8.8
  --restart unless-stopped \
  estrellaxd/auto_bangumi:latest

```

### 选项2: 使用 Docker-compose 部署

复制以下内容到 `docker-compose.yml` 文件中，然后运行 `docker-compose up -d` 即可。

```yaml
version: "3.8"

services:
  AutoBangumi:
    image: estrellaxd/auto_bangumi:latest
    container_name: AutoBangumi
    volumes:
      - AutoBangumi_config:/app/config
      - AutoBangumi_data:/app/data
    ports:
      - 7892:7892
    restart: unless-stopped
    dns:
      - 223.5.5.5
    network_mode: bridge

volumes:
    AutoBangumi_config:
        name: AutoBangumi_config
    AutoBangumi_data:
        name: AutoBangumi_data
```

## 安装 qBittorrent

如果你没有安装 qBittorrent，请先安装 qBittorrent。

- [在 Docker 中安装 qBittorrent][qbittorrent-docker]
- [在 Windows/macOS 中安装 qBittorrent][qbittorrent-desktop]
- [在 Linux 中安装 qBittorrent-nox][qbittorrent-nox]

## 获取 Mikan Project 的 RSS 链接

进入 [MiKan Project][mikan-project]，注册账号并登录，然后点击右下角的 **RSS** 按钮，复制链接。

![mikan-rss](../image/rss/rss-token.png){data-zoomable}

获取的 RSS 地址如下：

```txt
https://mikanani.me/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 或者
https://mikanime.tv/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
复制 token= 后面的内容。

详细步骤参考 [Mikan RSS][config-rss]


## 配置 AutoBangumi

安装好 AB 之后，AB 的 WebUI 会自动运行，但是主程序会处于暂停状态，可以进入 `http://abhost:7892` 进行配置。

1. 填入下载器的地址，端口，用户名和密码。

![ab-webui](../image/config/downloader.png){width=500}{class=ab-shadow-card}

2. 填入 Mikan RSS 的 Token。

![ab-rss](../image/config/parser.png){width=500}{class=ab-shadow-card}

3. 点击 **Apply** 保存配置，此时 AB 会重启运行，当右上角的圆点变为绿色时，表示 AB 已经正常运行。

[docker-engine]: https://docs.docker.com/engine/install/
[docker-desktop]: https://www.docker.com/products/docker-desktop
[config-rss]: ../config/rss
[mikan-project]: https://mikanani.me/
[qbittorrent-docker]: https://hub.docker.com/r/superng6/qbittorrent
[qbittorrent-desktop]: https://www.qbittorrent.org/download
[qbittorrent-nox]: https://www.qbittorrent.org/download-nox