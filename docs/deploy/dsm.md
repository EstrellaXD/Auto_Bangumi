# 群晖 NAS（DSM 7.2）部署（威联通类似）

DSM 7.2 支持 Docker Compose，因此我们建议使用 Docker Compose 进行一键部署。

## 创建配置和数据目录

在 `/volume1/docker/` 下创建 `AutoBangumi` 文件夹，然后在其中创建 `config` 和 `data` 子文件夹。

## 安装 Container Manager（Docker）套件

打开套件中心，安装 Container Manager（Docker）套件。

![install-docker](../image/dsm/install-docker.png){data-zoomable}

## 通过 Docker Compose 安装 AB

点击**项目**，然后点击**新增**，选择 **Docker Compose**。

![new-compose](../image/dsm/new-compose.png){data-zoomable}

将以下内容复制粘贴到 **Docker Compose** 中：
```yaml
version: "3.4"

services:
  ab:
    image: "ghcr.io/estrellaxd/auto_bangumi:latest"
    container_name: "auto_bangumi"
    restart: unless-stopped
    ports:
      - "7892:7892"
    volumes:
      - "./config:/app/config"
      - "./data:/app/data"
    network_mode: bridge
    environment:
      - TZ=Asia/Shanghai
      - AB_METHOD=Advance
      - PGID=1000
      - PUID=1000
      - UMASK=022
```

点击**下一步**，然后点击**完成**。

![create](../image/dsm/create.png){data-zoomable}

创建完成后，访问 `http://<NAS IP>:7892` 进入 AB 并进行配置。

## 通过 Docker Compose 安装 AB 和 qBittorrent

当您同时拥有代理和 IPv6 时，在群晖 NAS 的 Docker 中配置 IPv6 可能比较复杂。我们建议将 AB 和 qBittorrent 都安装在主机网络上以降低复杂性。

以下配置假设您已在 Docker 中部署了 Clash 代理，可通过本地 IP 的指定端口访问。

按照上一节的方法，调整并将以下内容粘贴到 **Docker Compose** 中：

```yaml
  qbittorrent:
    container_name: qbittorrent
    image: linuxserver/qbittorrent
    hostname: qbittorrent
    environment:
      - PGID=1000  # 根据需要修改
      - PUID=1000  # 根据需要修改
      - WEBUI_PORT=8989
      - TZ=Asia/Shanghai
    volumes:
      - ./qb_config:/config
      - your_anime_path:/downloads # 修改为您的番剧存储目录。在 AB 中将下载路径设置为 /downloads
    networks:
      - host
    restart: unless-stopped

  auto_bangumi:
    container_name: AutoBangumi
    environment:
      - TZ=Asia/Shanghai
      - PGID=1000  # 根据需要修改
      - PUID=1000  # 根据需要修改
      - UMASK=022
      - AB_DOWNLOADER_HOST=127.0.0.1:8989  # 根据需要修改端口
    volumes:
      - /volume1/docker/ab/config:/app/config
      - /volume1/docker/ab/data:/app/data
    network_mode: host
    environment:
      - AB_METHOD=Advance
    dns:
      - 8.8.8.8
    restart: unless-stopped
    image: "ghcr.io/estrellaxd/auto_bangumi:latest"
    depends_on:
      - qbittorrent

```

## 附加说明

PGID 和 PUID 的值需要根据您的系统确定。对于较新的群晖 NAS 设备，通常为：`PUID=1026, PGID=100`。修改 qBittorrent 端口时，请确保在所有位置都进行更新。

代理设置请参阅：[代理设置](../config/proxy)

在性能较低的设备上，默认配置可能会大量占用 CPU，导致 AB 无法连接到 qB，qB WebUI 也无法访问。

对于 220+ 等设备，建议使用以下 qBittorrent 设置以降低 CPU 使用率：

- 设置 -> 连接 -> 连接限制
  - 全局最大连接数：300
  - 每个种子最大连接数：60
  - 全局上传槽位限制：15
  - 每个种子上传槽位：4
- BitTorrent
  - 最大活动检查种子数：1
  - 种子队列
    - 最大活动下载数：3
    - 最大活动上传数：5
    - 最大活动种子数：10
- RSS
  - RSS 阅读器
    - 每个订阅源最大文章数：50
