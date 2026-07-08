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

セクション：`downloader`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `type` | ダウンローダー種類 | 文字列 | ダウンローダー種類 | `qbittorrent` |
| `host` | ダウンローダーアドレス | 文字列 | ホスト | `172.17.0.1:8080` |
| `username` | ユーザー名 | 文字列 | ユーザー名 | `admin` |
| `password` | パスワードまたはaria2 RPC secret | 文字列 | パスワード | `adminadmin` |
| `path` | ダウンロードパス | 文字列 | ダウンロードパス | `/downloads/Bangumi` |
| `ssl` | HTTPSを使う | 真偽値 | SSL | `false` |
