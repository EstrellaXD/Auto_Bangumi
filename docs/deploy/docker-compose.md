# 使用 Docker Compose 部署

使用 `docker-compose.yml` 文件一键部署 **AutoBangumi**。

## 安装 Docker Compose

Docker Compose 通常与 Docker 捆绑安装。使用以下命令检查：

```bash
docker compose -v
```

如果未安装，请使用以下命令安装：

```bash
$ sudo apt-get update
$ sudo apt-get install docker-compose-plugin
```

## 部署 **AutoBangumi**

### 创建 AutoBangumi 和数据目录

```bash
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

### 方式一：自定义 Docker Compose 配置

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
    restart: unless-stopped
    dns:
      - 8.8.8.8
    network_mode: bridge
    environment:
      - TZ=Asia/Shanghai
      - PGID=$(id -g)
      - PUID=$(id -u)
      - UMASK=022
```

将以上内容复制到 `docker-compose.yml` 文件中。

### 方式二：下载 Docker Compose 配置文件

如果您不想手动创建 `docker-compose.yml` 文件，项目提供了预制的配置：

- 仅安装 **AutoBangumi**：
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/AutoBangumi/docker-compose.yml
  ```
- 安装 **qBittorrent** 和 **AutoBangumi**：
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/qBittorrent+AutoBangumi/docker-compose.yml
  ```

选择您的安装方式并运行命令下载 `docker-compose.yml` 文件。如有需要，可以使用文本编辑器自定义参数。

### 定义环境变量

如果您使用的是下载的 AB+QB Docker Compose 文件，需要定义以下环境变量：

```shell
export \
QB_PORT=<YOUR_PORT>
```

- `QB_PORT`：输入您现有的 qBittorrent 端口或您想要的自定义端口，例如 `8080`

### 启动 Docker Compose

```bash
docker compose up -d
```
