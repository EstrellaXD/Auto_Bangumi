# クイックスタート

AutoBangumiはDockerでのデプロイを推奨しています。
デプロイ前に、[Docker Engine][docker-engine]または[Docker Desktop][docker-desktop]がインストールされていることを確認してください。

## データと設定ディレクトリの作成

ABのデータと設定を更新時に永続化するために、バインドマウントまたはDockerボリュームの使用を推奨します。

```shell
# バインドマウントを使用
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

バインドマウントまたはDockerボリュームのいずれかを選択：

```shell
# Dockerボリュームを使用
docker volume create AutoBangumi_config
docker volume create AutoBangumi_data
```

## DockerでAutoBangumiをデプロイ

これらのコマンドを実行する際は、AutoBangumiディレクトリにいることを確認してください。

### オプション1：Docker CLIでデプロイ

以下のコマンドをコピーして実行：

```shell
docker run -d \
  --name=AutoBangumi \
  -v ${HOME}/AutoBangumi/config:/app/config \
  -v ${HOME}/AutoBangumi/data:/app/data \
  -p 7892:7892 \
  -e TZ=Asia/Tokyo \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  -e UMASK=022 \
  --network=bridge \
  --dns=8.8.8.8 \
  --restart unless-stopped \
  ghcr.io/estrellaxd/auto_bangumi:latest
```

### オプション2：Docker Composeでデプロイ

以下の内容を`docker-compose.yml`ファイルにコピー：

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
    network_mode: bridge
    restart: unless-stopped
    dns:
      - 8.8.8.8
    environment:
      - TZ=Asia/Tokyo
      - PGID=$(id -g)
      - PUID=$(id -u)
      - UMASK=022
```

以下のコマンドでコンテナを起動：

```shell
docker compose up -d
```

## qBittorrentのインストール

qBittorrentをまだインストールしていない場合は、最初にインストールしてください：

- [DockerでqBittorrentをインストール][qbittorrent-docker]
- [Windows/macOSでqBittorrentをインストール][qbittorrent-desktop]
- [Linuxでqbittorrent-noxをインストール][qbittorrent-nox]

## 集約RSSリンクの取得（Mikan Projectを例として）

[Mikan Project][mikan-project]にアクセスし、アカウントを登録してログインし、右下の**RSS**ボタンをクリックしてリンクをコピーします。

![mikan-rss](/image/rss/rss-token.png){data-zoomable}

RSS URLは以下のようになります：

```txt
https://mikanani.me/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# または
https://mikanime.tv/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

詳細な手順については、[Mikan RSS設定][config-rss]を参照してください。


## AutoBangumiの設定

ABをインストール後、WebUIは自動的に起動しますが、メインプログラムは一時停止状態です。`http://abhost:7892`にアクセスして設定できます。

1. Webページを開きます。デフォルトのユーザー名は`admin`、デフォルトのパスワードは`adminadmin`です。初回ログイン後すぐに変更してください。
2. ダウンローダーのアドレス、ポート、ユーザー名、パスワードを入力します。

![ab-webui](/image/config/downloader.png){width=500}{class=ab-shadow-card}

3. **適用**をクリックして設定を保存します。ABが再起動し、右上のドットが緑色になると、ABが正常に動作していることを示します。

4. 右上の**+**ボタンをクリックし、**集約RSS**にチェックを入れ、パーサータイプを選択し、Mikan RSS URLを入力します。

![ab-rss](/image/config/add-rss.png){width=500}{class=ab-shadow-card}

ABが集約RSSを解析するのを待ちます。解析が完了すると、自動的にアニメを追加し、ダウンロードを管理します。



[docker-engine]: https://docs.docker.com/engine/install/
[docker-desktop]: https://www.docker.com/products/docker-desktop
[config-rss]: ../config/rss
[mikan-project]: https://mikanani.me/
[qbittorrent-docker]: https://hub.docker.com/r/superng6/qbittorrent
[qbittorrent-desktop]: https://www.qbittorrent.org/download
[qbittorrent-nox]: https://www.qbittorrent.org/download-nox
