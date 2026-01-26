# Downloader Settings

## WebUI Configuration

![downloader](../image/config/downloader.png){width=500}{class=ab-shadow-card}

<br/>

- **Downloader Type** is the downloader type. Currently only qBittorrent is supported.
- **Host** is the downloader address. [See below](#downloader-address)
- **Download path** is the mapped download path for the downloader. [See below](#download-path-issues)
- **SSL** enables SSL for the downloader connection.

## Common Issues

### Downloader Address

::: warning Note
Do not use 127.0.0.1 or localhost as the downloader address.
:::

Since AB runs in Docker with **Bridge** mode in the official tutorial, using 127.0.0.1 or localhost will resolve to AB itself, not the downloader.
- If your qBittorrent also runs in Docker, we recommend using the Docker **gateway address: 172.17.0.1**.
- If your qBittorrent runs on the host machine, use the host machine's IP address.

If you run AB in **Host** mode, you can use 127.0.0.1 instead of the Docker gateway address.

::: warning Note
Macvlan isolates container networks. Without additional bridge configuration, containers cannot access other containers or the host itself.
:::

### Download Path Issues

The path configured in AB is only used to generate the corresponding anime file path. AB itself does not directly manage files at that path.

**What should I put for the download path?**

This parameter just needs to match your **downloader's** configuration:
- Docker: If qB uses `/downloads`, then set `/downloads/Bangumi`. You can change `Bangumi` to anything.
- Linux/macOS: If it's `/home/usr/downloads` or `/User/UserName/Downloads`, just append `/Bangumi` at the end.
- Windows: Change `D:\Media\` to `D:\Media\Bangumi`

## `config.json` Configuration Options

The corresponding options in the configuration file are:

Configuration section: `downloader`

| Parameter | Description          | Type    | WebUI Option          | Default              |
|-----------|---------------------|---------|----------------------|---------------------|
| type      | Downloader type     | String  | Downloader type      | qbittorrent         |
| host      | Downloader address  | String  | Downloader address   | 172.17.0.1:8080     |
| username  | Downloader username | String  | Downloader username  | admin               |
| password  | Downloader password | String  | Downloader password  | adminadmin          |
| path      | Download path       | String  | Download path        | /downloads/Bangumi  |
| ssl       | Enable SSL          | Boolean | Enable SSL           | false               |
