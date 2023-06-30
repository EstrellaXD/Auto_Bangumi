# WSL 配置说明

感谢 #73 的贡献

WSL 用户可以用以下 `docker-compose.yml` 配置文件来部署 AutoBangumi

```yml
version: "3.6"
services:
  qbittorrent:
    container_name: qbittorrent
    image: johngong/qbittorrent:latest
    hostname: qbittorrent
    environment:
      - QB_EE_BIN=false
      - UID=1000  # 用户权限1000 当前WSL登录用户，查询方法 wsl内输入 id 用户名
      - GID=1000
      - QB_WEBUI_PORT=8989
    ports:
      - 6881:6881
      - 6881:6881/udp
      - 8989:8989
    volumes:
      - qb_config:/config
      - /mnt/g/animation:/Downloads   #下载路径，对应 Windows上目录是 G:\animation
    networks:
      - AutoBangumi_network
    restart: unless-stopped

  AutoBangumi:
    image: estrellaxd/auto_bangumi:latest
    container_name: AutoBangumi
    ports:
      - 7892:7892
    depends_on:
      - qbittorrent
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Asia/Shanghai
      - AB_DOWNLOADER_HOST=qbittorrent:8989
      - AB_DOWNLOADER_USERNAME=admin 
      - AB_DOWNLOADER_PASSWORD=adminadmin 
      - AB_NOT_CONTAIN=720|繁体|CHT|JPTC|繁日|BIG5
      - AB_DOWNLOAD_PATH=/Downloads  #qbittorrent 映射的地址，否者可能提示下载失败
      - AB_RSS=https://mikanani.me/RSS/MyBangumi?token=xxxxxxxx%3d%3d  #订阅地址，改成自己的
    networks:
      - AutoBangumi_network
    restart: unless-stopped

networks:
  AutoBangumi_network:
volumes:
  qb_config:
    external: false
  auto_bangumi:
    external: false

```