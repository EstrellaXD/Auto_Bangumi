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

Section: `downloader`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `type` | Downloader type | string | Downloader Type | `qbittorrent` |
| `host` | Downloader address | string | Host | `172.17.0.1:8080` |
| `username` | Downloader username | string | Username | `admin` |
| `password` | Downloader password or aria2 RPC secret | string | Password | `adminadmin` |
| `path` | Download path | string | Download Path | `/downloads/Bangumi` |
| `ssl` | Enable HTTPS | boolean | SSL | `false` |
