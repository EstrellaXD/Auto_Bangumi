# 快速开始

我们推荐使用 Docker 部署 AutoBangumi。
部署前，请确保已安装 [Docker Engine][docker-engine] 或 [Docker Desktop][docker-desktop]。

## 创建数据和配置目录

为确保 AB 的数据和配置在更新时持久化，我们建议使用绑定挂载或 Docker 卷。

```shell
# 使用绑定挂载
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

选择绑定挂载或 Docker 卷：

```shell
# 使用 Docker 卷
docker volume create AutoBangumi_config
docker volume create AutoBangumi_data
```

## 使用 Docker 部署 AutoBangumi

运行这些命令时，请确保您在 AutoBangumi 目录中。

### 方式一：使用 Docker CLI 部署

复制并运行以下命令：

```shell
docker run -d \
  --name=AutoBangumi \
  -v ${HOME}/AutoBangumi/config:/app/config \
  -v ${HOME}/AutoBangumi/data:/app/data \
  -p 7892:7892 \
  -e TZ=Asia/Shanghai \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  -e UMASK=022 \
  --network=bridge \
  --dns=8.8.8.8 \
  --restart unless-stopped \
  ghcr.io/estrellaxd/auto_bangumi:latest
```

### 方式二：使用 Docker Compose 部署

将以下内容复制到 `docker-compose.yml` 文件中：

```yaml
version: "3.8"

services:
  AutoBangumi:
    image: "ghcr.io/estrellaxd/auto_bangumi:latest"
    container_name: AutoBangumi
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    ports:
      - "7892:7892"
    network_mode: bridge
    restart: unless-stopped
    dns:
      - 8.8.8.8
    environment:
      - TZ=Asia/Shanghai
      - PGID=$(id -g)
      - PUID=$(id -u)
      - UMASK=022
```

运行以下命令启动容器：

```shell
docker compose up -d
```

## 安装 qBittorrent

如果您尚未安装 qBittorrent，请先安装：

- [在 Docker 中安装 qBittorrent][qbittorrent-docker]
- [在 Windows/macOS 上安装 qBittorrent][qbittorrent-desktop]
- [在 Linux 上安装 qBittorrent-nox][qbittorrent-nox]

## 获取聚合 RSS 链接（以 Mikan Project 为例）

访问 [Mikan Project][mikan-project]，注册账号并登录，然后点击右下角的 **RSS** 按钮并复制链接。

![mikan-rss](../image/rss/rss-token.png){data-zoomable}

RSS 链接格式如下：

```txt
https://mikanani.me/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 或
https://mikanime.tv/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

详细步骤请参阅 [Mikan RSS 设置][config-rss]。


## 配置 AutoBangumi

安装 AB 后，WebUI 将自动启动，但主程序处于暂停状态。您可以访问 `http://abhost:7892` 进行配置。

1. 打开网页。默认用户名为 `admin`，默认密码为 `adminadmin`。首次登录后请立即修改。
2. 输入下载器的地址、端口、用户名和密码。

![ab-webui](../image/config/downloader.png){width=500}{class=ab-shadow-card}

3. 点击**应用**保存配置。AB 将重启，当右上角的圆点变为绿色时，表示 AB 正常运行。

4. 点击右上角的 **+** 按钮，勾选**聚合 RSS**，选择解析器类型，然后输入您的 Mikan RSS 链接。

![ab-rss](../image/config/add-rss.png){width=500}{class=ab-shadow-card}

等待 AB 解析聚合 RSS。解析完成后，将自动添加番剧并管理下载。



[docker-engine]: https://docs.docker.com/engine/install/
[docker-desktop]: https://www.docker.com/products/docker-desktop
[config-rss]: ../config/rss
[mikan-project]: https://mikanani.me/
[qbittorrent-docker]: https://hub.docker.com/r/superng6/qbittorrent
[qbittorrent-desktop]: https://www.qbittorrent.org/download
[qbittorrent-nox]: https://www.qbittorrent.org/download-nox
