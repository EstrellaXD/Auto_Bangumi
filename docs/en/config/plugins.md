# Plugin Settings

From 4.0, downloaders, rename methods, notification channels, search sites and other functions connect through plugin extension points. The `plugins` section of `config.json` keeps the enable switches, the plugin options and the provider choices.

## WebUI

Manage plugins under **Settings → Plugins**:

- **Allow unsigned plugins**: plugins from the local directory (`config/plugins/local/`) or from pip are unsigned. They load only when this switch is on. Plugins run inside the AutoBangumi process with full privileges. Enable only plugins that you trust.
- **Enabled**: the switch on each plugin card.
- **Options**: expand the card, fill in the form that the plugin declares, then click **Save options**.

These three settings apply immediately. You do not need to click **Save & restart**.

Each plugin card shows the source (built-in, local, pip), the state (running, disabled, error) and the declared permissions. If a plugin fails to load, or is disabled automatically after 5 failures in sequence, the card shows the reason. When you change the options of that plugin, AutoBangumi tries to load it again.

These settings are not on the plugin page. They are in the related settings sections and are saved with the global configuration (**Save & restart**):

- Downloader instances and the default downloader: [Downloader Settings](/en/config/downloader#multiple-downloaders)
- Rename method and revision conflict policy: [Bangumi Manager](/en/config/manager)

## Built-in plugins

| id | Default | Function | Details |
| --- | --- | --- | --- |
| `rename` | enabled | rename methods `pn`, `advance`, `template` | [Bangumi Manager](/en/config/manager#template-rename) |
| `ingest-filters` | enabled | include filter: when you set a list of regular expressions (case-insensitive), only torrents whose name matches one of them are downloaded. Empty means no filter. It applies to all subscriptions | see below |
| `media-server-refresh` | enabled | refreshes Jellyfin / Emby / Plex after organizing. Without a server URL and an API key it does nothing | [Bangumi Manager](/en/config/manager#media-server-refresh) |
| `hardlink` | disabled | hard-links organized files into a media library | [Bangumi Manager](/en/config/manager#hard-links-to-a-media-library) |

The include filter of `ingest-filters` (`include`) adds to the exclude filter of each rule. An invalid regular expression is matched as literal text.

To write plugins, see [Plugin development](/en/dev/plugins).

## `config.json`

Section: `plugins`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `allow_unsigned` | Load unsigned plugins (local directory, pip) | boolean | Allow unsigned plugins | `false` |
| `dev_mode` | Reload local plugins when their files change | boolean | config only | `false` |
| `enabled` | Enable switch per plugin id | object | Enabled switch on the plugin card | `{}` |
| `options` | Options per plugin id | object | Options on the plugin card | `{}` |
| `hook_order` | Hook order per extension point | object | config only | `{}` |
| `slots` | Provider selected for each extension point | object | see below | see below |
| `instances` | Instances of multi-instance extension points (now only downloaders) | array | Downloader Settings | one qBittorrent instance with id `default` |

- A plugin that is not in `enabled`: a built-in plugin follows its manifest (enabled, except `hardlink`). A plugin from another source is disabled.
- Values in `options` must pass the validation of the plugin's config model. The WebUI rejects invalid options on save. The API masks password-type fields in its responses.
- The keys of `hook_order` are hook extension points: `torrent.filter`, `title.parsed`, `torrent.adding`, `http.request`, `message_template`. The values are lists of plugin ids. Listed plugins run first, in the listed order. The other plugins follow, sorted by priority and then by plugin id.

### `slots`

| Key | Description | WebUI field | Default |
| --- | --- | --- | --- |
| `downloader` | Id of the default downloader instance. It must be a downloader instance in `instances` | **Set default** in Downloader Settings | `default` |
| `rename_strategy` | Rename method: `none` (host), `pn`, `advance`, `template` (built-in `rename` plugin), or a method from another plugin | Rename Method in Bangumi Manager | `pn` |
| `conflict_policy` | What to do when a higher revision targets an existing episode: `hold` keeps the existing file, `replace` replaces it with the higher revision | Revision Conflict Policy in Bangumi Manager | `hold` |
| `media_files` | Classifies the files in a torrent as video or subtitle. The host implementation uses the file extension | config only | `default` |

If the selected provider is not registered (for example, its plugin is disabled or was stopped after failures), `rename_strategy` is handled as `none`, and `conflict_policy` and `media_files` use the host implementation.

### `instances`

```json
"instances": [
    {
        "id": "default",
        "point": "downloader",
        "provider": "qbittorrent",
        "options": { "host": "172.17.0.1:8080", "username": "admin", "password": "adminadmin", "path": "/downloads/Bangumi", "ssl": false }
    }
]
```

| Key | Description |
| --- | --- |
| `id` | Instance id. It must be unique |
| `point` | Extension point. Now only `downloader` |
| `provider` | Provider id that implements the extension point, for example `qbittorrent`, `aria2` or a downloader from a plugin |
| `options` | Options of the instance. For downloader fields, see [Downloader Settings](/en/config/downloader#config-json) |

## Upgrade from 3.3

On the first start after an upgrade to 4.0, AutoBangumi moves 3.3 settings into the `plugins` section:

- `downloader` → the downloader instance with id `default` in `plugins.instances`. `plugins.slots.downloader` is set to `default`.
- `bangumi_manage.rename_method` → `plugins.slots.rename_strategy` (the removed method `normal` becomes `none`).
- `bangumi_manage.revision_conflict_policy` → `plugins.slots.conflict_policy`.

Before the migration, AutoBangumi copies the original file to `config.json.v3.bak`. It does not overwrite an existing backup. It uses `config.json.v3.bak.1`, `config.json.v3.bak.2` and so on. If the migration fails (for example, the migrated configuration does not pass validation), AutoBangumi restores the original file from the backup and **does not start**. The log names the field that failed. Correct that field, then start again.
