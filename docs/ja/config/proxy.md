# プロキシとリバースプロキシ

## プロキシ

![proxy](/image/config/proxy.png){width=700}{class=ab-shadow-card}

AutoBangumiはHTTP、HTTPS、SOCKS5プロキシに対応しています。RSS、検索プロバイダー、TMDB、Bangumi、LLM providerなどの外部通信に使われます。

- **有効化**：プロキシを有効化します。
- **種類**：`http`、`https`、`socks5`。
- **ホスト / ポート**：プロキシのアドレスとポート。
- **ユーザー名 / パスワード**：認証が必要な場合に入力します。環境変数参照も利用できます。

変更後は **保存して再起動** をクリックしてください。

## `config.json`

セクション：`proxy`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `enable` | プロキシを有効化 | 真偽値 | 有効化 | `false` |
| `type` | プロキシ種類 | 文字列 | 種類 | `http` |
| `host` | プロキシホスト | 文字列 | ホスト | `""` |
| `port` | プロキシポート | 整数 | ポート | `0` |
| `username` | ユーザー名 | 文字列 | ユーザー名 | `""` |
| `password` | パスワード | 文字列 | パスワード | `""` |

## リバースプロキシ

Mikan Projectにアクセスできない場合は、RSS内の `mikanani.me` を `mikanime.tv` に置き換えるか、Cloudflare Workersなどで独自のリバースプロキシを構築できます。
