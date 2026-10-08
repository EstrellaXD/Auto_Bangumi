# Upgrade from 3.3 to 4.0

4.0 is a large release that adds plugins. You can now have more than one downloader instance. Built-in plugins now supply rename, hard links, torrent filters, and media server refresh. At the first start, AB moves the 3.3 configuration to the new locations. This page tells what the migration changes, how to upgrade, what to check after the upgrade, and how to roll back to 3.3.

::: warning 4.0 is a beta
4.0 is only available as `4.0.0-beta.N` beta releases. Until the 4.0 stable release, the `latest` image tag continues to point to 3.3. Make the backups below before you upgrade a production system.
:::

## Before you upgrade

1. **Make sure that you use 3.3.x.** You can upgrade to 4.0 only from 3.3.x. AB does not start if it finds data from an older version: a version below 3.3 in `config/version.info`, or a 2.x `data/data.json` file. The log tells you to upgrade to the latest 3.3.x and start it once. At that time, AB can already have changed `config.json` to the 4.0 format. Copy `config.json.v3.bak` back to `config.json` before you go back to 3.3.x.
2. **Stop the container. Back up the `config` and `data` directories.** You need these backups to roll back to 3.3 (see [Roll back to 3.3](#roll-back-to-3-3)).

```shell
docker stop AutoBangumi
cp -a ${HOME}/AutoBangumi/config ${HOME}/AutoBangumi/config.bak-3.3
cp -a ${HOME}/AutoBangumi/data ${HOME}/AutoBangumi/data.bak-3.3
```

## Change the image tag

Image tags for the 4.0 beta:

| Tag | Meaning |
| --- | --- |
| `4.0.0-beta.N` | One specified beta, for example `4.0.0-beta.1`. **Recommended**: you control when you upgrade and roll back |
| `dev-latest` | The most recent beta. Each `X.Y.Z-beta.N` release moves this tag, not only 4.0 releases |
| `latest` | The most recent stable release. This is 3.3 until the 4.0 stable release |

The images are on `ghcr.io/estrellaxd/auto_bangumi` and on Docker Hub as `estrellaxd/auto_bangumi`.

Docker Compose: change `image`, then create the container again.

```yaml
services:
  AutoBangumi:
    image: "ghcr.io/estrellaxd/auto_bangumi:4.0.0-beta.1"
```

```shell
docker compose pull
docker compose up -d
```

Docker CLI: remove the old container. Then run `docker run` again with the new tag and the same options.

The volumes (`/app/config`, `/app/data`), the port, and the environment variables do not change. 4.0 adds no environment variables. AB installs plugins in `config/plugins/`, which is in the `/app/config` volume.

### In-app update (3.3 beta channel)

If you selected the beta update channel in 3.3, **Settings → Software Update** shows `4.0.0-beta.N`. 4.0 update bundles need image version `4.0.0-beta.1` or later. On a 3.3 image, **Update now** fails with a message that the image is too old and that you must pull a newer image. Change the image tag as the previous section tells you. Users on the stable channel do not see 4.0 betas.

## First start: configuration migration

Before AB reads `config.json`, it checks if the file has the 3.3 format. If it does, AB first copies the file to `config.json.v3.bak`. Then AB moves these fields to their 4.0 locations:

| 3.3 field | 4.0 location |
| --- | --- |
| `downloader` | The downloader instance with id `default` in `plugins.instances`. `type` becomes `provider`. The other fields (host, username, password, download path, SSL) go into `options` |
| — | `plugins.slots.downloader` is set to `"default"` (the default downloader instance) |
| `bangumi_manage.rename_method` | `plugins.slots.rename_strategy`. The deprecated value `normal` becomes `none`, which has the same behavior |
| `bangumi_manage.revision_conflict_policy` | `plugins.slots.conflict_policy` |
| `token` of a Bark channel | `device_key` |
| `chat_id` of a WeCom channel | `webhook_url` |

Example of the downloader configuration before and after the migration:

::: code-group

```json [3.3]
{
  "downloader": {
    "type": "qbittorrent",
    "host": "172.17.0.1:8080",
    "username": "admin",
    "password": "adminadmin",
    "path": "/downloads/Bangumi",
    "ssl": false
  },
  "bangumi_manage": {
    "rename_method": "pn",
    "revision_conflict_policy": "hold"
  }
}
```

```json [4.0]
{
  "plugins": {
    "slots": {
      "downloader": "default",
      "rename_strategy": "pn",
      "conflict_policy": "hold"
    },
    "instances": [
      {
        "id": "default",
        "point": "downloader",
        "provider": "qbittorrent",
        "options": {
          "host": "172.17.0.1:8080",
          "username": "admin",
          "password": "adminadmin",
          "path": "/downloads/Bangumi",
          "ssl": false
        }
      }
    ]
  }
}
```

:::

The example shows only the related fields. The other settings do not change.

- **AB does not overwrite a backup.** If `config.json.v3.bak` already exists (for example, you rolled back to 3.3 and upgrade again), AB writes the new backup to `config.json.v3.bak.1`, `config.json.v3.bak.2`, and so on. The first backup contains the oldest 3.3 configuration.
- **If the migration is successful**, the log shows `Migrated config.json to 4.0 (...); the 3.3 file is kept as config.json.v3.bak`. The parentheses list the fields that moved.
- **If the migration fails**, `config.json` keeps its 3.3 content and AB does not start. The log shows the field that caused the failure. Correct that field and start AB again.
- AB does not migrate a configuration that already has the 4.0 format, and does not make a backup for it.
- Environment variables (`AB_DOWNLOADER_HOST`, `AB_METHOD`, and others) continue to work. AB reads them only at the first start, when no `config.json` exists. AB writes their values to the default downloader instance and to `plugins.slots`.

During the same start, AB upgrades the database to schema v26. It adds the plugin storage table `plugin_kv` and a `downloader_id` column to bangumi, movies, RSS subscriptions, and torrents. Existing torrents belong to the `default` instance. Existing rules and subscriptions have an empty `downloader_id`, which means that they use the default instance.

## Behavior that changes in 4.0

### More than one downloader

In **Settings → Downloader Setting**, you can add more than one downloader instance (qBittorrent, aria2, or a downloader from a plugin) and set the default instance. Rules and RSS subscriptions can select a downloader. If you do not select one, AB uses the default instance. Each torrent records its downloader, and AB renames and deletes the torrent on that downloader. Refer to [Downloader Settings](../config/downloader).

### Rename is a plugin

The built-in plugin `rename` supplies `pn`, `advance`, and the new `template` method. It is enabled by default. AB itself supplies `none`. The output of `pn` and `advance` is the same as in 3.3.

- `template` makes file names from a template that you write. When you save the settings, AB renders the template as a test. AB does not save a template that is not valid.
- If the template fails for a file at run time, the file keeps its name and AB sends a "Files kept their names" notification. AB does not use `pn` as a fallback.
- If you disable the `rename` plugin in **Settings → Plugins**, AB uses `none` for all bangumi and keeps the original file names.

Refer to [Bangumi Manager](../config/manager).

### Hard links to a media library

The new built-in plugin `hardlink` is **disabled by default**. When you enable it, AB links the video and subtitle files of each organized torrent into the media library directory. The download directory does not change and continues to seed.

- If the downloader and AB see different paths (for example, they run in different containers), set a path map in `path_map` for each downloader instance.
- If a hard link is not possible (different file systems), AB copies the file by default (`cross_device: copy`).
- In Docker, you must also mount the media library directory into the AB container. For hard links, keep the download directory and the media library on the same disk, and mount them into the container through one mount point.

Refer to [Bangumi Manager](../config/manager).

### Other built-in plugins

- The torrent filter plugin `ingest-filters` is enabled by default. If its `include` option is empty, it does not filter torrents.
- The plugin `media-server-refresh` is enabled by default. It sends refresh requests only after you set the Jellyfin / Emby / Plex address and API key.

### Third-party plugins

Plugins from the local directory (`config/plugins/local/`) or from pip do not have a signature. AB loads them only when you turn on "Allow unsigned plugins" (`plugins.allow_unsigned`) in **Settings → Plugins**. To write a plugin, refer to [Plugin Development](../dev/plugins).

### Removed items

- The 3.2-compatible GET control endpoints (`/api/v1/restart`, `/start`, `/stop`, `/shutdown`) and `GET /api/v1/auth/refresh_token`. Use POST. Change the scripts that call these endpoints.
- The old `experimental_openai` configuration section and the old single-channel notification fields. 3.3 already moved them to `llm` and `notification.providers`.

## Checks after the upgrade

- [ ] The log has the line `Migrated config.json to 4.0`. The `config` directory has `config.json.v3.bak`.
- [ ] **Settings → Downloader Setting** has an instance with id `default`. Its host, username, and download path are the same as in 3.3, and AB can connect to it.
- [ ] The rename method is the same as in 3.3. The 3.3 value `normal` now shows as `none`. The behavior is the same: AB does not rename files.
- [ ] The `rename` plugin is enabled in **Settings → Plugins**.
- [ ] If you use Bark or WeCom notifications, send a test notification.
- [ ] If you want hard links or media server refresh, enable and configure them in **Settings → Plugins**.
- [ ] Scripts that use the 3.2 GET control endpoints now use POST.

## Roll back to 3.3

4.x writes its version to `config/version_v4.info` and does not change `config/version.info`. Thus 3.3 reads the correct data version when it starts. When 4.x starts on 3.3 data for the first time, AB makes a backup of the database at `data/data.db.v3.bak`.

**If you have a full backup from before the upgrade** (recommended):

1. Stop the container.
2. Replace the `config` and `data` directories with `config.bak-3.3` and `data.bak-3.3`.
3. Change the image tag back to 3.3 (for example `3.3.6`). Create the container again.

All changes that you made in 4.0 (new bangumi, new subscriptions, new settings) are lost.

**If you do not have a full backup:**

1. Stop the container.
2. Copy `config/config.json.v3.bak` to `config/config.json`. 3.3 does not know `plugins.instances`. If you do not restore the file, the downloader settings go back to their default values.
3. Copy `data/data.db.v3.bak` to `data/data.db`. 3.3 cannot use the database after 4.0 changed its tables.
4. If you used the in-app update in 4.0, remove the `config/updates/` directory. If you do not, the 3.3 image loads the newer 4.0 code from that directory at startup.
5. Change the image tag back to 3.3 (for example `3.3.6`). Create the container again.

This procedure goes back to the state at the time of the upgrade. The bangumi, torrent records and settings that you added or changed in 4.0 are lost.

When you upgrade to 4.0 again, the migration runs again and writes the new backup to `config.json.v3.bak.1`.
