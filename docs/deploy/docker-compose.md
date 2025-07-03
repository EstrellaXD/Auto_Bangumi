# 通过 Docker Compose 部署 AutoBangumi

现在提供了一键部署的 **AutoBangumi** 的方法，可以使用 `docker-compose.yml` 文件进行部署。

## 安装 Docker Compose

正常来说安装完 Docker 之后都会自带 `docker-compose`，使用命令：

```bash
docker compose -v
```

检查版本即可

如果没有安装，可以使用以下命令安装：

```bash
 $ sudo apt-get update
 $ sudo apt-get install docker-compose-plugin
```

## 部署 **AutoBangumi**

### 创建 AutoBangumi及数据 文件夹

```bash
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

### 选项1: 自定义 Docker Compose 配置文件

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
      - 223.5.5.5
    network_mode: bridge
    environment:
      - TZ=Asia/Shanghai
      - PGID=$(id -g)
      - PUID=$(id -u)
      - UMASK=022
```

复制上面的内容到 `docker-compose.yml` 文件中。

### 选项2: 下载 Docker Compose 配置文件

当你不想自己创建 `docker-compose.yml` 文件时，
项目中提供了三种安装方式：

- 只安装 **AutoBangumi**
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/AutoBangumi/docker-compose.yml
  ```
- 安装 **qBittorrent** 与 **AutoBangumi**
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/qBittorrent+AutoBangumi/docker-compose.yml
  ```

首先选择你要安装的方式，**拷贝上面的命令运行即可**，这一步是下载 `docker-compose.yml` 配置文件，如果需要自定义可以使用文本编辑器对其中的参数进行自定义。

### 定义环境变量

如果你是用上面下载的 AB+QB / AB+QB+Plex 的 Docker-Compose 文件，那么你需要定义以下环境变量：

```shell
export \
QB_PORT=<YOUR_PORT>
```

- `QB_PORT`: 填写你的已经部署的 qBittorrent 端口号，或者想要自定义的端口号，比如: `8080`

### 拉起 Docker-Compose

```bash
# 如果配置过了上面的环境变量，请使用下面的方式拉起
docker compose up -d
```

### 选项3: 在 Windows 平台，使用 Docker Desktop 部署 AutoBangumi 及 qBittorrent

```yaml
version: "3.4"
services:
  qbittorrent:
    container_name: qbittorrent
    image: superng6/qbittorrent:4.6.0_v2.0.9 # 4.6.0_v2.0.9 配置正常版本
    hostname: qbittorrent
    environment:
      - PUID=1026
      - PGID=100
      - TZ=Asia/Shanghai
    volumes:
      - ./qb_config:/config
      - ./downloads:/downloads # 注意 修改此处为自己存放动漫的目录,ab 内下载路径填写downloads
    network_mode: bridge
    ports:
      - 6881:6881
      - 6881:6881/udp
      - 8080:8080
    restart: unless-stopped

  AutoBangumi:
    image: "ghcr.io/estrellaxd/auto_bangumi:latest"
    container_name: AutoBangumi
    depends_on:
      - qbittorrent
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    network_mode: bridge
    ports:
      - "7892:7892"
    dns:
      - 223.5.5.5
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
      - PUID=1026
      - PGID=100
      - UMASK=022
```

::: warning 注意
这里如果想通过 **桥接模式** 模式将两个容器连接起来，两个容器均需要配置为桥接模式
:::

另外，该版本的 **qbittorrent** 在首次启动 或 在未在配置文件中设置登陆密码时，会在 **Docker Desktop** 的日志文件中提示本次会话的临时密码，使用临时密码登陆系统后可以通过更改 **Web UI** 设置中的 **验证** 项固定密码，详细可见[关于新版本qBittorrent“无效的用户名和密码”，其实可以这么解决](https://zhuanlan.zhihu.com/p/685581375)，文章中演示的是群晖的部署情况，实测和 **Windows** 演示差不多。

