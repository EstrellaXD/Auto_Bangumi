# 使用 Docker CLI 部署

## 新版本说明

从 AutoBangumi 2.6 开始，您可以直接在 WebUI 中配置所有设置。您可以先启动容器，然后在 WebUI 中进行配置。旧版本的环境变量配置将自动迁移。环境变量仍然有效，但仅在首次启动时生效。

## 创建数据和配置目录

为确保 AB 的数据和配置在更新时持久化，我们建议使用 Docker 卷或绑定挂载。

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

## 使用 Docker CLI 部署 AutoBangumi

复制并运行以下命令。

请确保您的工作目录为 AutoBangumi。

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

如果使用 Docker 卷，请相应替换绑定路径：
```shell
  -v AutoBangumi_config:/app/config \
  -v AutoBangumi_data:/app/data \
```

AB WebUI 将自动启动，但主程序处于暂停状态。访问 `http://abhost:7892` 进行配置。

AB 会自动将环境变量写入 `config.json` 并开始运行。

我们建议使用 _[Portainer](https://www.portainer.io)_ 或类似的 Docker 管理界面进行高级部署。
