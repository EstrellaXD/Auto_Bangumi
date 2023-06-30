## 安装 **Docker Compose**

现在提供了一键部署的 **AutoBangumi** 的方法，可以使用 `docker-compose.yml` 文件进行部署。

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

### 创建 AutoBangumi 文件夹

```bash
mkdir AutoBangumi
cd AutoBangumi
```

### 下载 Docker Compose 配置文件

项目中提供了三种安装方式：

- 只安装 **AutoBangumi**
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/docker-compose/AutoBangumi/docker-compose.yml
  ```
- 安装 **qBittorrent** 与 **AutoBangumi**
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/docker-compose/qBittorrent+AutoBangumi/docker-compose.yml
  ```
- **qBittorrent** + **AutoBangumi** + **Plex**
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/docker-compose/All-in-one/docker-compose.yml
  ```

首先选择你要安装的方式，**拷贝上面的命令运行即可**，这一步是下载 `docker-compose.yml` 配置文件，如果需要自定义可以使用文本编辑器对其中的参数进行自定义。

### 定义环境变量

如果你是用上面下载的 AB+QB / AB+QB+Plex 的 Docker-Compose 文件，那么你需要定义以下环境变量：

```shell
export \
QB_PORT=<YOUR_PORT> \
DOWNLOAD_PATH=<YOUR_DOWNLOAD_PATH>
```

- `QB_PORT`: 填写你的已经部署的 qBittorrent 端口号，或者想要自定义的端口号，比如: `8080`
- `DOWNLOAD_PATH`: 填写你的文件下载路径

如果你不想使用环境变量，也可以拉起 Docker-Compose 后在 WebUI 中进行配置。

### 拉起 Docker-Compose

```bash
# 如果配置过了上面的环境变量，请使用下面的方式拉起
docker compose up -d

# 如果没有手动配置上面的环境变量，请使用下面的方式拉起
QB_PORT=<QB_PORT> DOWNLOAD_PATH=<YOUR_DOWNLOAD_PATH> docker compose up -d
```

## 部署结果：

```other
2022-06-05 16:38:49 INFO: Add RSS Feed successfully.
2022-06-05 16:38:50 INFO: Adding Kawaii dake ja Nai Shikimori-san Season 1
2022-06-05 16:38:50 INFO: Adding Kakkou no Iinazuke Season 1
2022-06-05 16:38:50 INFO: Adding SPYxFAMILY Season 1
2022-06-05 16:38:50 INFO: Adding Love Live！虹咲学园 学园偶像同好会 Season 2
2022-06-05 16:38:50 INFO: Adding CUE! Season 1
2022-06-05 16:38:50 INFO: Adding Kaguya-sama wa Kokurasetai Season 3
2022-06-05 16:38:50 INFO: Adding Shokei Shoujo no Virgin Road Season 1
2022-06-05 16:38:50 INFO: Adding Kakkou no Iikagen Season 1
2022-06-05 16:38:50 INFO: Adding Summer Time Rendering Season 1
2022-06-05 16:38:50 INFO: Adding Mahoutsukai Reimeiki Season 1
2022-06-05 16:38:50 INFO: Adding Paripi Koumei Season 1
2022-06-05 16:38:50 INFO: Adding Komi-san wa, Komyushou Desu. Season 1
2022-06-05 16:38:50 INFO: Adding Deaimon Season 1
2022-06-05 16:38:50 INFO: Adding Tate no Yuusha no Nariagari Season 2
2022-06-05 16:38:50 INFO: Adding Shijou Saikyou no Daimaou Season 1
2022-06-05 16:38:50 INFO: Adding Yuusha, Yamemasu Season 1
2022-06-05 16:38:50 INFO: Adding Tomodachi Game Season 1
2022-06-05 16:38:50 INFO: Adding Machikado Mazoku: 2-choume Season 1
2022-06-05 16:38:50 INFO: Start collecting past episodes.
2022-06-05 16:39:32 INFO: Start adding rules.
2022-06-05 16:39:32 INFO: Finished.
2022-06-05 16:39:32 INFO: Waiting for downloading torrents...
2022-06-05 16:49:32 INFO: Finished checking 185 file's name.
2022-06-05 16:49:32 INFO: Renamed 0 files.
2022-06-05 16:49:32 INFO: Finished rename process.
```
