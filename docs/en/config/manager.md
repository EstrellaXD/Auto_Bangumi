# Bangumi Manager

## WebUI

![manager](/image/config/manager.png){width=700}{class=ab-shadow-card}

- **Enable**: enables file organization and rename behavior.
- **Rename Method**:
  - `pn`: keeps more release-title information, using a `Torrent title S0XE0X` style.
  - `advance`: uses official title and standard season/episode naming.
  - `none`: do not rename files.
  - `template`: name files with your own template, see [Template rename](#template-rename).
  - Plugins can provide more rename methods; enabled ones appear in the drop-down.
- **EPS complete**: tries to backfill missing episodes in the current season.
- **Add Group Tag**: adds subgroup-related tags to downloader tasks.
- **Delete Bad Torrent**: removes errored downloader tasks.
- **Track Unmatched Torrents**: stores torrents that do not match any rule as orphan records. Disable it if you want newly added rules to catch old feed items immediately, at the cost of rechecking those old items on each RSS refresh.

## Template rename

With `template`, file names come from the built-in **Template Rename** plugin (`rename-template`). Edit the templates under **Settings → Plugins → Template Rename**:

| Option | Used for | Default |
| --- | --- | --- |
| Episode template | regular episodes | `{{ title }} S{{ season\|pad(2) }}E{{ episode\|pad(2) }}` |
| Movie template | movies | `{{ title }}` |

The defaults produce exactly the same names as `pn`. Templates use sandboxed [Jinja2](https://jinja.palletsprojects.com/) syntax with these variables: `title` (parsed from the file name), `bangumi_name` (folder name, e.g. `Frieren (2023)`), `season` (season offset already applied), `episode` (episode offset applied; half episodes keep the fraction, e.g. `12.5`), `group` (may be empty), `episode_type` (`episode` / `movie` / `special`), `kind` (`media` / `subtitle`) and `language` (subtitle language, empty for media). The `pad(n)` filter zero-pads numbers: `{{ episode|pad(3) }}` gives `005`.

- The template only renders the base name; the extension is appended for you (`.zh.ass` style for subtitles).
- If a template renders an empty name, contains `/` or `\`, or uses an unknown variable, that file keeps its name and an error is logged.
- Templates with syntax errors are rejected when you save them.
- Changing the method or the template only affects downloads completed afterwards; already organized torrents are not renamed again.

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
