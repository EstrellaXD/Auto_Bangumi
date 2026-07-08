# ネットワーク設定

![network](/image/config/network.png){width=700}{class=ab-shadow-card}

ネットワーク設定では外部メタデータサービスのURLと認証情報を上書きできます。変更後は **保存して再起動** をクリックしてください。

- **TMDB API URL**：既定値は `https://api.themoviedb.org`。
- **TMDB API Key（任意）**：空の場合は内蔵共有Keyを使います。個人Keyを設定すると共有Keyのレート制限を避けられます。
- **Bangumi API URL**：既定値は `https://api.bgm.tv`。

## `config.json`

セクション：`network`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `tmdb_base_url` | TMDB API URL | 文字列 | TMDB API URL | `https://api.themoviedb.org` |
| `tmdb_api_key` | カスタムTMDB API Key | 文字列 | TMDB API Key | `""` |
| `bgm_base_url` | Bangumi API URL | 文字列 | Bangumi API URL | `https://api.bgm.tv` |
