# Built-in Plugins

Built-in plugins are part of AB. They are in `module/plugins/builtin/`. They use the same SDK as third-party plugins, so you can use them as a reference. Enable, disable and configure them in Settings → Plugins.

| id | Default | Purpose |
| --- | --- | --- |
| `rename` | Enabled | The rename strategies `pn`, `advance` and `template` |
| `ingest-filters` | Enabled | The include filter (`torrent.filter`) |
| `media-server-refresh` | Enabled | Refresh Jellyfin / Emby / Plex after organizing (it does nothing until you set the address and key) |
| `hardlink` | Disabled | Hard-link organized files into the media library |

## rename

The host has only `none` (keep the name). `pn` names a file with the title that AB parsed from the file name. `advance` uses the series folder name. Their output is byte-identical to 3.x. `template` renders the file name stem with a sandboxed Jinja2 template.

::: v-pre
Enter the template in Settings → Plugins → rename, for example `{{ title }} - S{{ season|pad(2) }}E{{ episode|pad(2) }}`. Variables: `title`, `bangumi_name`, `season`, `episode`, `episode_type`, `group`, `kind`, `language`. The filter `pad(n)` pads with zeros and keeps the fraction of a half episode. AB renders the template one time when you save. An invalid template is refused (HTTP 422). If rendering fails at run time, or the result is empty or has a path separator, the file keeps its name and AB sends a notification. AB **does not fall back to `pn`**.
:::

## ingest-filters

Adds an include filter. The rule already has an exclude filter. Set a list of regular expressions (case-insensitive). AB then downloads only torrents whose name matches at least one. An empty list means no filter. An invalid regular expression is matched as literal text.

## media-server-refresh

Subscribes to `torrent.organized` and to `hardlink.linked`, which `hardlink` publishes when it places new files in the library. After the first event, it waits `delay` seconds. The events in this time share one refresh request. An event that arrives after the request is sent causes one more refresh.

| Option | Description |
| --- | --- |
| `server` | `jellyfin`, `emby` or `plex` |
| `url` | The server address, for example `http://192.168.1.10:8096` (Plex default port 32400). Empty means no refresh |
| `api_key` | The API key of Jellyfin / Emby, or the `X-Plex-Token` of Plex |
| `delay` | The delay in seconds. Default 30 |

## hardlink

Subscribes to `torrent.organized` and links media files and subtitles into the media library directory. The download directory stays as it is and the torrent keeps seeding.

| Option | Description |
| --- | --- |
| `source_root` | The download root (an AB local path). The library keeps the same structure: `library_root / (file path relative to source_root)` |
| `library_root` | The media library directory (an AB local path). It must not be inside `source_root` |
| `path_map` | `[{downloader, from, to}]`: replaces the downloader path prefix `from` with the AB local path `to`. `downloader` defaults to `default`. The longest prefix wins. A path with no match is used as it is |
| `cross_device` | When a hard link crosses file systems (EXDEV): `copy` (default), `symlink` or `skip` (skip and notify) |

- At first enable, `source_root` and `library_root` are empty and the plugin shows a load failure. The settings form is already visible. After you fill the fields and save, the plugin reloads.
- The plugin writes the link or copy to a temporary file next to the target, then renames it atomically. An interrupted copy leaves no half file.
- If the library has a file with the same name that this plugin did not create, the plugin skips it, does not overwrite it, and sends a `hardlink.failed` notification.
- A link that this plugin made for the same episode is replaced atomically after a version upgrade (a new version replaces the old torrent and the canonical name stays the same). The new link points to the new file.
- When the plugin receives an event for a file that is already linked, it does nothing. It records the targets that it created in its own key-value store. If the user deletes a file that the plugin placed, a new event does not create it again. Only a backfill creates it again.
- **Deleting a torrent does not delete the links in the library.**
- AB does not process files that were downloaded before you enabled the plugin. Click "Link existing files" in the settings section of the plugin, or call `POST /api/v1/plugins/hardlink/backfill`. It walks `.mp4` / `.mkv` / `.ass` / `.srt` files under `source_root` and returns the counts `{"linked", "exists", "conflict", "failed"}`.

::: tip Docker
A hard link cannot cross file systems. In Docker, put the download directory and the media library on the same disk. Map them into the AB container with **one mount point** (for example, mount `/mnt/media` as `/media` and keep both directories under it). Two separate mounts count as different file systems, even on the same disk. Then the link falls back to the `cross_device` behavior. If the downloader runs in another container and sees different paths, use `path_map`.
:::
