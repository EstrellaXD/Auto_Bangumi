## 快速开始

我们推荐你在 Docker 中部署运行 AutoBangumi。
部署前请确认已经安装了 [Docker Engine][docker-engine] 或者 [Docker Desktop][docker-desktop]。

### 创建数据和配置文件夹

为了保证 AB 在每次更新之后数据和配置不丢失，推荐使用 Docker volume 进行数据和配置的持久化。

```shell
docker volume create AutoBangumi_config
docker volume create AutoBangumi_data
```

### 使用 Docker-cli 部署 AutoBangumi

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

### 使用 Docker-compose 部署 AutoBangumi

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

### 配置 AutoBangumi

此时 AB 的 WebUI 会自动运行，但是主程序会处于暂停状态，可以进入 `http://abhost:7892` 进行配置。


[docker-engine]: https://docs.docker.com/engine/install/
[docker-desktop]: https://www.docker.com/products/docker-desktop