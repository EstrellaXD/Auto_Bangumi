# Docker Composeでデプロイ

`docker-compose.yml`ファイルを使用した**AutoBangumi**のワンクリックデプロイ方法です。

::: tip 4.0 ベータ版
このページのコマンドは `latest` タグを使い、3.3 の正式版をインストールします。4.0 ベータ版を使うには、イメージタグを `4.0.0-beta.N`（例：`4.0.0-beta.1`）に変更してください。ボリュームと環境変数は変わりません。3.3 からアップグレードする前に [3.3 から 4.0 へのアップグレード](./upgrade-4.0) を読んでください。4.0 のハードリンクプラグインを使う場合は、メディアライブラリのフォルダーもコンテナにマウントする必要があります。[アニメ管理設定](../config/manager) を参照してください。
:::

## Docker Composeのインストール

Docker Composeは通常Dockerにバンドルされています。以下で確認してください：

```bash
docker compose -v
```

インストールされていない場合は、以下でインストールしてください：

```bash
$ sudo apt-get update
$ sudo apt-get install docker-compose-plugin
```

## **AutoBangumi**のデプロイ

### AutoBangumiとデータディレクトリの作成

```bash
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

### オプション1：カスタムDocker Compose設定

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
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    dns:
      - 8.8.8.8
    network_mode: bridge
    environment:
      - TZ=Asia/Shanghai
      - PGID=$(id -g)
      - PUID=$(id -u)
      - UMASK=022
```

上記の内容を`docker-compose.yml`ファイルにコピーしてください。

### オプション2：Docker Compose設定ファイルのダウンロード

`docker-compose.yml`ファイルを手動で作成したくない場合、プロジェクトでは事前に作成された設定を提供しています：

- **AutoBangumi**のみをインストール：
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/AutoBangumi/docker-compose.yml
  ```
- **qBittorrent**と**AutoBangumi**をインストール：
  ```bash
  wget https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/main/docs/resource/docker-compose/qBittorrent+AutoBangumi/docker-compose.yml
  ```

インストール方法を選択し、コマンドを実行して`docker-compose.yml`ファイルをダウンロードしてください。必要に応じてテキストエディタでパラメータをカスタマイズできます。

### 環境変数の定義

ダウンロードしたAB+QB Docker Composeファイルを使用している場合は、以下の環境変数を定義する必要があります：

```shell
export \
QB_PORT=<YOUR_PORT>
```

- `QB_PORT`：既存のqBittorrentポートまたは希望するカスタムポートを入力します。例：`8080`

### Docker Composeの起動

```bash
docker compose up -d
```
