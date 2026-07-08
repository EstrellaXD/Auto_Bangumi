# Network Settings

![network](/image/config/network.png){width=700}{class=ab-shadow-card}

Network settings override external metadata endpoints and credentials. Click **Save & restart** after changing them.

- **TMDB API URL**: default `https://api.themoviedb.org`.
- **TMDB API Key (optional)**: leave empty to use the built-in shared key. A personal key can avoid shared-key rate limits.
- **Bangumi API URL**: default `https://api.bgm.tv`.

## `config.json`

Section: `network`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `tmdb_base_url` | TMDB API URL | string | TMDB API URL | `https://api.themoviedb.org` |
| `tmdb_api_key` | Custom TMDB API key | string | TMDB API Key | `""` |
| `bgm_base_url` | Bangumi API URL | string | Bangumi API URL | `https://api.bgm.tv` |
