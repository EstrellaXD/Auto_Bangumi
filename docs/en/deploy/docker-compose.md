# Deploy with Docker Compose

A one-click deployment method for **AutoBangumi** using a `docker-compose.yml` file.

## Install Docker Compose

Docker Compose usually comes bundled with Docker. Check with:

```bash
docker compose -v
```

If not installed, install it with:

```bash
$ sudo apt-get update
$ sudo apt-get install docker-compose-plugin
```

## Deploy **AutoBangumi**

### Create AutoBangumi and Data Directories

```bash
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

### Option 1: Custom Docker Compose Configuration

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

Copy the above content into a `docker-compose.yml` file.

### Option 2: Download Docker Compose Configuration File

If you don't want to create the `docker-compose.yml` file manually, the project provides pre-made configurations:

- Install **AutoBangumi** only:
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/AutoBangumi/docker-compose.yml
  ```
- Install **qBittorrent** and **AutoBangumi**:
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/qBittorrent+AutoBangumi/docker-compose.yml
  ```

Choose your installation method and run the command to download the `docker-compose.yml` file. You can customize parameters with a text editor if needed.

### Define Environment Variables

If you're using the downloaded AB+QB Docker Compose file, you need to define the following environment variables:

```shell
export \
QB_PORT=<YOUR_PORT>
```

- `QB_PORT`: Enter your existing qBittorrent port or your desired custom port, e.g., `8080`

### Start Docker Compose

```bash
docker compose up -d
```
