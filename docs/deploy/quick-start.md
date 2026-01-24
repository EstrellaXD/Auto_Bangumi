# Quick Start

We recommend deploying AutoBangumi in Docker.
Before deployment, make sure you have [Docker Engine][docker-engine] or [Docker Desktop][docker-desktop] installed.

## Create Data and Configuration Directories

To ensure AB's data and configuration persist across updates, we recommend using bind mounts or Docker volumes.

```shell
# Using bind mount
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

Choose either bind mount or Docker volume:

```shell
# Using Docker volume
docker volume create AutoBangumi_config
docker volume create AutoBangumi_data
```

## Deploy AutoBangumi with Docker

Make sure you are in the AutoBangumi directory when running these commands.

### Option 1: Deploy with Docker CLI

Copy and run the following command:

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

### Option 2: Deploy with Docker Compose

Copy the following content into a `docker-compose.yml` file:

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

Run the following command to start the container:

```shell
docker compose up -d
```

## Install qBittorrent

If you haven't installed qBittorrent, please install it first:

- [Install qBittorrent in Docker][qbittorrent-docker]
- [Install qBittorrent on Windows/macOS][qbittorrent-desktop]
- [Install qBittorrent-nox on Linux][qbittorrent-nox]

## Get an Aggregated RSS Link (Using Mikan Project as an Example)

Visit [Mikan Project][mikan-project], register an account and log in, then click the **RSS** button in the bottom right corner and copy the link.

![mikan-rss](../image/rss/rss-token.png){data-zoomable}

The RSS URL will look like:

```txt
https://mikanani.me/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# or
https://mikanime.tv/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

For detailed steps, see [Mikan RSS Setup][config-rss].


## Configure AutoBangumi

After installing AB, the WebUI will start automatically, but the main program will be paused. You can access `http://abhost:7892` to configure it.

1. Open the webpage. The default username is `admin` and the default password is `adminadmin`. Change these immediately after first login.
2. Enter your downloader's address, port, username, and password.

![ab-webui](../image/config/downloader.png){width=500}{class=ab-shadow-card}

3. Click **Apply** to save the configuration. AB will restart, and when the dot in the upper right corner turns green, it indicates AB is running normally.

4. Click the **+** button in the upper right corner, check **Aggregated RSS**, select the parser type, and enter your Mikan RSS URL.

![ab-rss](../image/config/add-rss.png){width=500}{class=ab-shadow-card}

Wait for AB to parse the aggregated RSS. Once parsing is complete, it will automatically add anime and manage downloads.



[docker-engine]: https://docs.docker.com/engine/install/
[docker-desktop]: https://www.docker.com/products/docker-desktop
[config-rss]: ../config/rss
[mikan-project]: https://mikanani.me/
[qbittorrent-docker]: https://hub.docker.com/r/superng6/qbittorrent
[qbittorrent-desktop]: https://www.qbittorrent.org/download
[qbittorrent-nox]: https://www.qbittorrent.org/download-nox
