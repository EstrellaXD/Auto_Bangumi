# 群晖 (DSM 7.2) 部署说明（ QNAP 同理）

在 DSM 7.2 中，已经支持了 Docker Compose，推荐使用 Docker Compose 一键部署本项目。

## 创建配置和数据存储文件夹

‼️在 `/volume1/docker/` 下创建 `ab` 文件夹，然后在 `ab` 文件夹下创建 `config` 和 `data` 文件夹。

## 安装 Container Manager (Docker) 套件

进入套件中心，安装 Container Manager (Docker) 套件。

![install-docker](../image/dsm/install-docker.png){data-zoomable}

## 通过 Docker compose 安装配置 AB

点击 **项目**，然后点击 **新建**，选择 **Docker Compose**。

![new-compose](../image/dsm/new-compose.png){data-zoomable}

复制以下内容填入 **Docker Compose** 中。
```yaml
version: "3.8"

services:
  ab:
    image: "ghcr.io/estrellaxd/auto_bangumi:latest"
    container_name: "auto_bangumi"
    restart: unless-stopped
    ports:
      - "7892:7892"
    volumes:
      - "/volume1/docker/ab/config:/app/config"
      - "/volume1/docker/ab/data:/app/data"
```

点击 **下一步**，然后点击 **完成**。

![create](../image/dsm/create.png){data-zoomable}

完成创建之后进入 `http://<NAS IP>:7892` 即可进入 AB 并进行配置。



