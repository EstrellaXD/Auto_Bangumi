# ダウンローダー設定

## WebUI

![downloader](/image/config/downloader.png){width=700}{class=ab-shadow-card}

![downloader type](/image/config/downloader-type.png){width=700}{class=ab-shadow-card}

- **ダウンローダー種類**：`qbittorrent` または `aria2`。
- **ホスト**：Web APIまたはRPCのアドレスです。
- **ユーザー名 / パスワード**：qBittorrentはWebUIの認証情報を使います。aria2ではユーザー名は無視され、パスワード欄がRPC secretになります。
- **ダウンロードパス**：ダウンローダーから見える保存パスです。
- **SSL**：HTTPSで接続します。

変更後は **保存して再起動** をクリックしてください。

## アドレスの注意

::: warning
Docker Bridgeモードでは、ダウンローダーとAutoBangumiが同じネットワーク名前空間にない限り、`127.0.0.1` や `localhost` は使わないでください。
:::

- ダウンローダーもDocker内：同じDockerネットワークのサービス名、または `172.17.0.1:8080` などのゲートウェイを使います。
- ダウンローダーがホスト上：ホストのLAN IPを使います。
- AutoBangumiがHostネットワーク：`127.0.0.1` を使えます。
- aria2例：`172.17.0.1:6800`、RPC secretはパスワード欄に入力します。

## `config.json`

ダウンローダーは `plugins.instances` のうち `point` が `downloader` のインスタンスです。`plugins.slots.downloader` は既定インスタンスの id（既定値 `default`）です。設定画面は既定インスタンスを編集します。

```json
"plugins": {
    "slots": { "downloader": "default" },
    "instances": [
        {
            "id": "default",
            "point": "downloader",
            "provider": "qbittorrent",
            "options": { "host": "172.17.0.1:8080", "username": "admin", "password": "adminadmin", "path": "/downloads/Bangumi", "ssl": false }
        }
    ]
}
```

3.3 の `downloader` セクションは、4.0 へのアップグレード後の初回起動時に `default` インスタンスへ自動で移行され、元のファイルは `config.json.v3.bak` として保存されます。環境変数 `AB_DOWNLOADER_HOST`、`AB_DOWNLOADER_USERNAME`、`AB_DOWNLOADER_PASSWORD`、`AB_DOWNLOAD_PATH` は引き続き既定インスタンスに反映されます。

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `provider` | ダウンローダー種類 | 文字列 | ダウンローダー種類 | `qbittorrent` |
| `host` | ダウンローダーアドレス | 文字列 | ホスト | `172.17.0.1:8080` |
| `username` | ユーザー名 | 文字列 | ユーザー名 | `admin` |
| `password` | パスワードまたはaria2 RPC secret | 文字列 | パスワード | `adminadmin` |
| `path` | ダウンロードパス | 文字列 | ダウンロードパス | `/downloads/Bangumi` |
| `ssl` | HTTPSを使う | 真偽値 | SSL | `false` |
