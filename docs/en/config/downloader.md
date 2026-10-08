# Downloader Settings

## WebUI

![downloader](/image/config/downloader.png){width=700}{class=ab-shadow-card}

![downloader type](/image/config/downloader-type.png){width=700}{class=ab-shadow-card}

- **Downloader Type**: `qbittorrent` or `aria2`.
- **Host**: Web API or RPC address. See [Downloader address](#downloader-address).
- **Username / Password**: qBittorrent uses WebUI credentials. aria2 ignores username and uses the password field as the RPC secret.
- **Download Path**: the path as seen by the downloader. See [Download path](#download-path).
- **SSL**: use HTTPS when connecting to the downloader.

After changing downloader settings, click **Save & restart** so the downloader client is recreated.

## Downloader Address

::: warning
In Docker Bridge mode, do not use `127.0.0.1` or `localhost` unless the downloader and AutoBangumi share the same network namespace.
:::

- Downloader in Docker: use a service name on the same Docker network, or a gateway address such as `172.17.0.1:8080`.
- Downloader on the host: use the host LAN IP.
- AutoBangumi in Host network mode: `127.0.0.1` can be used.
- aria2 example: `172.17.0.1:6800`, with the RPC secret in the password field.

## Download Path

Use the path from the downloader's point of view:

- Docker: if the downloader sees `/downloads`, use `/downloads/Bangumi`.
- Linux/macOS: for example `/home/user/downloads/Bangumi`.
- Windows: for example `D:\Media\Bangumi`.

## `config.json`

A downloader is an entry in `plugins.instances` whose `point` is `downloader`. `plugins.slots.downloader` is the id of the default instance (`default` by default). The settings page edits the default instance:

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

On the first start after an upgrade to 4.0, the 3.3 `downloader` section moves to the `default` instance automatically. The original file is kept as `config.json.v3.bak`. The environment variables `AB_DOWNLOADER_HOST`, `AB_DOWNLOADER_USERNAME`, `AB_DOWNLOADER_PASSWORD` and `AB_DOWNLOAD_PATH` still work and set the default instance.

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `provider` | Downloader type | string | Downloader Type | `qbittorrent` |
| `host` | Downloader address | string | Host | `172.17.0.1:8080` |
| `username` | Downloader username | string | Username | `admin` |
| `password` | Downloader password or aria2 RPC secret | string | Password | `adminadmin` |
| `path` | Download path | string | Download Path | `/downloads/Bangumi` |
| `ssl` | Enable HTTPS | boolean | SSL | `false` |
