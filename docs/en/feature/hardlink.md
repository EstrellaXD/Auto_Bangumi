# Hard Links to a Media Library

The built-in `hardlink` plugin links videos and subtitles into a separate media library folder after AB organizes a torrent. The download folder does not change, and the torrent continues to seed. Your media server scans only the library folder.

This plugin is **disabled by default**. It runs after AB organizes each torrent. It also runs when the rename method is `none`.

## Enable the Plugin

1. Open **Settings → Plugins**. Find the `hardlink` plugin and expand **Options**.
2. Enter `source_root` (the download root) and `library_root` (the media library). Both are absolute paths as AB sees them. `library_root` must not be inside `source_root`.
3. If the downloader sees different paths than AB, add rows to `path_map` (see below).
4. Click **Save options**. Then set the **Enabled** switch to on.

The plugin works when its card shows "Running". AB checks the options when you save. If a path is not absolute, or the library is inside the download root, AB does not save the options.

The path of a file in the library is the same as its path relative to `source_root`:

```
source_root    /media/downloads/Bangumi
library_root   /media/library
/media/downloads/Bangumi/Frieren (2023)/Season 1/Frieren S01E05.mkv
>>
/media/library/Frieren (2023)/Season 1/Frieren S01E05.mkv
```

## Options

| Option | Description | Default |
| --- | --- | --- |
| `source_root` | Download root. An absolute path on the AB side. The library uses the same folder structure | None. Required |
| `library_root` | Media library. An absolute path on the AB side. It must not be inside `source_root` | None. Required |
| `path_map` | List of mappings from downloader paths to AB paths. See below | Empty |
| `cross_device` | What to do across file systems: `copy` copies the file, `symlink` makes a symbolic link, `skip` skips the file and sends a notification | `copy` |

## Path Map

The file paths in the "torrent organized" event are **the paths that the downloader sees**. If the downloader and AB run in different containers with different mount points, use `path_map` to change these paths into AB paths.

Each row has three fields:

- `downloader`: the downloader instance id. The default is `default`. Each downloader instance needs its own rows. See [Multiple Downloaders](./downloaders.md).
- `from`: the path prefix that the downloader sees.
- `to`: the same location as AB sees it.

AB uses only the rows with the same downloader id as the event. The longest matching prefix wins. AB uses a path without a match as it is.

Example: qBittorrent mounts the disk as `/downloads`. AB mounts the same disk as `/media/downloads`. A second downloader, `nas`, sees `/volume1/downloads`:

```json
"path_map": [
    { "downloader": "default", "from": "/downloads", "to": "/media/downloads" },
    { "downloader": "nas", "from": "/volume1/downloads", "to": "/media/nas" }
]
```

In the settings form, click **Add row** to add a mapping. Click **Remove** to remove a row.

The mapped path must be inside `source_root`. If it is not, AB does not process the file and sends a notification.

## Different Drives and Docker

A hard link can only exist on one file system. When `source_root` and `library_root` are on different file systems, AB uses the `cross_device` option:

- `copy` (default): copies the file and keeps its modification time. The library uses the same disk space again. A large file can take a long time to copy.
- `symlink`: makes a symbolic link. If you delete the file in the download folder, the link breaks.
- `skip`: does not process the file and sends a notification.

::: tip Docker
Put the download folder and the library on the same disk. Mount them into the AB container through **one mount point**. For example, mount all of `/mnt/media` as `/media`, and keep the download folder and the library below it. Two separate mounts are different file systems, even on the same disk. In that case, AB uses `cross_device`.
:::

AB first writes the link or copy to a temporary file next to the target (`.<name>.<random>.ab-hardlink`). Then AB renames it to the target in one atomic step. If a copy stops before it is complete, no partial file stays in the library.

## Files That Are Already in the Library

The plugin records each file that it puts into the library. When a file is already at the target:

| Condition | Result |
| --- | --- |
| The target is a hard link, symbolic link or same copy of the source | Done. AB does nothing |
| The plugin did not put the target there, or the target changed after the plugin put it there | AB skips the file, **never overwrites it**, and sends a notification |
| The target is an old file that the plugin put at the same location | Revision upgrade. AB replaces it with the new file in one atomic step |

**Revision upgrade**: when a new revision of a torrent (for example `v2`) replaces the old torrent, the organized file name does not change. The plugin replaces its old link with a link to the new file.

AB collects all problems of one torrent into one notification. The notification lists each file and the reason. It shows the torrent hash, not the torrent name.

## Link Existing Files

The plugin processes only torrents that AB organizes after you enable it. For files that you downloaded before, start a backfill:

1. Open **Settings**. Find the "Hardlink backfill" section at the end of the section list. This section shows only while the plugin runs.
2. Click **Link existing files**.

AB finds all `.mp4`, `.mkv`, `.ass` and `.srt` files below `source_root`. Then it shows four counts: linked, existing, conflict and failed. The backfill runs only when you click the button. It does not send notifications. AB does not process a file again if it is already linked. The backfill reads the download root on the AB side directly and does not use `path_map`.

You can also call `POST /api/v1/plugins/hardlink/backfill`. It returns the same counts.

## Deleted Torrents

When you delete a torrent, AB does not delete its files in the library. With hard links or copies, the library files continue to play after you delete the torrent and its files. With symbolic links, the links break.
