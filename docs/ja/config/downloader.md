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

## 複数のダウンローダー

設定セクションの上部にすべてのダウンローダーインスタンスが表示されます。インスタンスをクリックすると下で編集できます。新しい id を入力して **追加** をクリックするとインスタンスを作成できます。種類は qBittorrent、aria2、またはプラグインのダウンローダーです。**既定に設定** で既定インスタンスを変更します。既定インスタンスは削除できません。

- ルール編集（詳細設定）と購読の追加でダウンローダーを選べます。空欄なら既定インスタンスを使います。ダウンローダーが 1 つだけのときは表示されません。
- 新しいトレントはルールのダウンローダーに追加されます。ルールに指定がなければ購読のダウンローダー、それもなければ既定インスタンスです。購読から作成されたルールは購読の選択を引き継ぎます。
- 各トレントは追加先のダウンローダーを記録し、リネームと削除はそのダウンローダーで行います。ルールを別のダウンローダーに変えても、既存のトレントは元の場所に残ります。
- リネームはダウンローダーごとに実行されます。接続できないダウンローダーはスキップされ、初めて接続できなくなったときに「ダウンローダー接続エラー」が通知されます。他のダウンローダーは通常どおり処理されます。
- ダウンローダーが複数あるとき、ダウンローダーページとトレント一覧に各トレントのダウンローダーが表示されます。
- ダウンローダーを削除すると、それを選んでいたルールと購読は既定インスタンスを使います。削除したダウンローダー内の既存のトレントには影響しません。

## アドレスの注意

::: warning
Docker Bridgeモードでは、ダウンローダーとAutoBangumiが同じネットワーク名前空間にない限り、`127.0.0.1` や `localhost` は使わないでください。
:::

- ダウンローダーもDocker内：同じDockerネットワークのサービス名、または `172.17.0.1:8080` などのゲートウェイを使います。
- ダウンローダーがホスト上：ホストのLAN IPを使います。
- AutoBangumiがHostネットワーク：`127.0.0.1` を使えます。
- aria2例：`172.17.0.1:6800`、RPC secretはパスワード欄に入力します。

## `config.json`

ダウンローダーは `plugins.instances` のうち `point` が `downloader` のインスタンスです。`plugins.slots.downloader` は既定インスタンスの id（既定値 `default`）です。設定画面でインスタンスを追加するとき、id に使えるのは英数字、`_`、`-` だけです。

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

3.3 の `downloader` セクションは、4.0 へのアップグレード後の初回起動時に `default` インスタンスへ自動で移行され、元のファイルは `config.json.v3.bak` として保存されます。移行に失敗した場合は元のファイルを復元して起動を中止します。詳しくは [プラグイン設定](/ja/config/plugins) を参照してください。

環境変数 `AB_DOWNLOADER_HOST`、`AB_DOWNLOADER_USERNAME`、`AB_DOWNLOADER_PASSWORD`、`AB_DOWNLOAD_PATH` は、設定ファイルがまだない初回起動時にだけ読み込まれ、既定インスタンスに反映されます。`host`、`username`、`password` の値には `$VAR` 形式の環境変数参照を書けます。使用時に展開されます。

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `id` | インスタンス id | 文字列 | 新しいダウンローダー id | `default` |
| `provider` | ダウンローダー種類 | 文字列 | ダウンローダー種類 | `qbittorrent` |
| `host` | ダウンローダーアドレス | 文字列 | ホスト | `172.17.0.1:8080` |
| `username` | ユーザー名 | 文字列 | ユーザー名 | `admin` |
| `password` | パスワードまたはaria2 RPC secret | 文字列 | パスワード | `adminadmin` |
| `path` | ダウンロードパス | 文字列 | ダウンロードパス | `/downloads/Bangumi` |
| `ssl` | HTTPSを使う | 真偽値 | SSL | `false` |
