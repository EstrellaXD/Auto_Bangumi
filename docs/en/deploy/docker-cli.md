# Deploy with Docker CLI

::: tip 4.0 beta
The commands on this page use the `latest` tag, which installs the 3.3 stable release. To use the 4.0 beta, change the image tag to `4.0.0-beta.N` (for example `4.0.0-beta.1`). The volumes and the environment variables do not change. Before you upgrade from 3.3, read [Upgrade from 3.3 to 4.0](./upgrade-4.0). The 4.0 hard link plugin also needs the media library directory mounted into the container. Refer to [Bangumi Manager](../config/manager).
:::

## Note on New Versions

Since AutoBangumi 2.6, you can configure everything directly in the WebUI. You can start the container first and then configure it in the WebUI. Environment variable configuration from older versions will be automatically migrated. Environment variables still work but only take effect on the first startup.

## Create Data and Configuration Directories

To ensure AB's data and configuration persist across updates, we recommend using Docker volumes or bind mounts.

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

## Deploy AutoBangumi with Docker CLI

Copy and run the following command.

Make sure your working directory is AutoBangumi.

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
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  ghcr.io/estrellaxd/auto_bangumi:latest
```

If using Docker volumes, replace the bind paths accordingly:
```shell
  -v AutoBangumi_config:/app/config \
  -v AutoBangumi_data:/app/data \
```

The AB WebUI will start automatically, but the main program will be paused. Access `http://abhost:7892` to configure it.

AB will automatically write environment variables to `config.json` and start running.

We recommend using _[Portainer](https://www.portainer.io)_ or similar Docker management UIs for advanced deployment.
