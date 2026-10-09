# Docker CLIでデプロイ

::: tip 4.0 ベータ版
このページのコマンドは `latest` タグを使い、3.3 の正式版をインストールします。4.0 ベータ版を使うには、イメージタグを `4.0.0-beta.N`（例：`4.0.0-beta.1`）に変更してください。ボリュームと環境変数は変わりません。3.3 からアップグレードする前に [3.3 から 4.0 へのアップグレード](./upgrade-4.0) を読んでください。4.0 のハードリンクプラグインを使う場合は、メディアライブラリのフォルダーもコンテナにマウントする必要があります。[アニメ管理設定](../config/manager) を参照してください。
:::

## 新バージョンに関する注意

AutoBangumi 2.6以降、WebUIで直接すべてを設定できます。まずコンテナを起動してから、WebUIで設定できます。以前のバージョンの環境変数設定は自動的に移行されます。環境変数は引き続き機能しますが、初回起動時にのみ有効です。

## データと設定ディレクトリの作成

更新後もABのデータと設定が保持されるように、Dockerボリュームまたはバインドマウントの使用を推奨します。

```shell
# バインドマウントを使用
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

バインドマウントまたはDockerボリュームのいずれかを選択してください：
```shell
# Dockerボリュームを使用
docker volume create AutoBangumi_config
docker volume create AutoBangumi_data
```

## Docker CLIでAutoBangumiをデプロイ

以下のコマンドをコピーして実行してください。

作業ディレクトリがAutoBangumiであることを確認してください。

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

Dockerボリュームを使用する場合は、バインドパスを適宜置き換えてください：
```shell
  -v AutoBangumi_config:/app/config \
  -v AutoBangumi_data:/app/data \
```

AB WebUIは自動的に起動しますが、メインプログラムは一時停止状態です。`http://abhost:7892`にアクセスして設定してください。

ABは自動的に環境変数を`config.json`に書き込み、実行を開始します。

高度なデプロイには_[Portainer](https://www.portainer.io)_または同様のDocker管理UIの使用を推奨します。
