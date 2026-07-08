# Bangumi Manager

## WebUI

![manager](/image/config/manager.png){width=700}{class=ab-shadow-card}

- **Enable**: enables file organization and rename behavior.
- **Rename Method**:
  - `normal`: conservative title and episode naming.
  - `pn`: keeps more release-title information, using a `Torrent title S0XE0X` style.
  - `advance`: uses official title and standard season/episode naming.
  - `none`: do not rename files.
- **EPS complete**: tries to backfill missing episodes in the current season.
- **Add Group Tag**: adds subgroup-related tags to downloader tasks.
- **Delete Bad Torrent**: removes errored downloader tasks.
- **Track Unmatched Torrents**: stores torrents that do not match any rule as orphan records. Disable it if you want newly added rules to catch old feed items immediately, at the cost of rechecking those old items on each RSS refresh.

## `config.json`

Section: `bangumi_manage`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `enable` | Enable manager | boolean | Enable | `true` |
| `eps_complete` | Enable episode completion | boolean | EPS complete | `false` |
| `rename_method` | Rename method | string | Rename Method | `pn` |
| `group_tag` | Add subgroup tags | boolean | Add Group Tag | `false` |
| `remove_bad_torrent` | Delete errored torrents | boolean | Delete Bad Torrent | `false` |
| `track_orphans` | Track unmatched torrents | boolean | Track Unmatched Torrents | `true` |
