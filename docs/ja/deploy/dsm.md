# Synology NAS（DSM 7.2）デプロイ（QNAPも同様）

DSM 7.2はDocker Composeをサポートしているため、ワンクリックデプロイにDocker Composeの使用を推奨します。

## 設定とデータディレクトリの作成

`/volume1/docker/`の下に`AutoBangumi`フォルダを作成し、その中に`config`と`data`サブフォルダを作成します。

## Container Manager（Docker）パッケージのインストール

パッケージセンターを開き、Container Manager（Docker）パッケージをインストールします。

![install-docker](/image/dsm/install-docker.png){data-zoomable}

## Docker Compose経由でABをインストール

**プロジェクト**をクリックし、**作成**をクリックして、**Docker Compose**を選択します。

![new-compose](/image/dsm/new-compose.png){data-zoomable}

以下の内容をコピーして**Docker Compose**に貼り付けます：
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

**次へ**をクリックし、**完了**をクリックします。

![create](/image/dsm/create.png){data-zoomable}

作成後、`http://<NAS IP>:7892`にアクセスしてABに入り、設定を行います。

## Docker Compose経由でABとqBittorrentをインストール

プロキシとIPv6の両方がある場合、Synology NASのDockerでIPv6を設定するのは複雑です。複雑さを軽減するために、ABとqBittorrentの両方をホストネットワークにインストールすることを推奨します。

以下の設定は、DockerにデプロイされたローカルIPの指定ポートでアクセス可能なClashプロキシがあることを前提としています。

前のセクションに従って、以下の内容を調整して**Docker Compose**に貼り付けます：

```yaml
  qbittorrent:
    container_name: qbittorrent
    image: linuxserver/qbittorrent
    hostname: qbittorrent
    environment:
      - PGID=1000  # 必要に応じて変更
      - PUID=1000  # 必要に応じて変更
      - WEBUI_PORT=8989
      - TZ=Asia/Shanghai
    volumes:
      - ./qb_config:/config
      - your_anime_path:/downloads # アニメ保存ディレクトリに変更してください。ABでダウンロードパスを/downloadsに設定
    networks:
      - host
    restart: unless-stopped

  auto_bangumi:
    container_name: AutoBangumi
    environment:
      - TZ=Asia/Shanghai
      - PGID=1000  # 必要に応じて変更
      - PUID=1000  # 必要に応じて変更
      - UMASK=022
      - AB_DOWNLOADER_HOST=127.0.0.1:8989  # 必要に応じてポートを変更
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

## 追加の注意事項

PGIDとPUIDの値はシステムに応じて決定する必要があります。新しいSynology NASデバイスでは、通常`PUID=1026, PGID=100`です。qBittorrentのポートを変更する場合は、すべての場所で更新してください。

プロキシ設定については、[プロキシ設定](/ja/config/proxy)を参照してください。

低性能マシンでは、デフォルト設定がCPUを大量に使用し、ABがqBに接続できなくなり、qB WebUIにアクセスできなくなる可能性があります。

220+などのデバイスでは、CPU使用率を下げるための推奨qBittorrent設定：

- 設定 -> 接続 -> 接続制限
  - グローバル最大接続数：300
  - Torrentあたりの最大接続数：60
  - グローバルアップロードスロット制限：15
  - Torrentあたりのアップロードスロット：4
- BitTorrent
  - 最大アクティブチェックTorrent数：1
  - Torrentキューイング
    - 最大アクティブダウンロード数：3
    - 最大アクティブアップロード数：5
    - 最大アクティブTorrent数：10
- RSS
  - RSSリーダー
    - フィードあたりの最大記事数：50
