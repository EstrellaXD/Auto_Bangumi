# File Renaming

AB has four rename methods: `pn`, `advance`, `template` and `none`. Select one in **Settings → Manage Setting → Rename Method**. The default is `pn`.

Since 4.0, plugins supply the rename methods:

- AB supplies `none`. It is always available.
- The built-in `rename` plugin supplies `pn`, `advance` and `template`. This plugin is enabled by default.
- Other plugins can add rename methods. When you enable such a plugin, its methods appear in the drop-down.

If you disable the `rename` plugin in **Settings → Plugins**, AB handles every series as `none`. The same occurs when AB disables the plugin after 5 errors in a row. When the selected method is not available, AB writes one log entry and uses `none`.

### pn

Short for `pure name`. This method uses the title that AB parses from the file name.

Example:
```
[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six S01E01.mkv
```

### advance

Advanced renaming. This method uses the name of the series folder.

```
/downloads/Bangumi/86 - Eighty Six(2023)/Season 1/[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six(2023) S01E01.mkv
```

`pn` and `advance` give the same result as in 3.x. Movies do not get `SxxExx`. Subtitle files get the language before the extension, for example `.zh.ass`.

### template

This method uses your own template. Write the template in the `template` option of the `rename` plugin in **Settings → Plugins**.

### none

No renaming. Files keep their names.

## Template Rename

::: v-pre
The default template is below. For normal episodes it gives the same result as `pn`. For movies, `pn` adds no `SxxExx`, but the default template does:

```
{{ title }} S{{ season|pad(2) }}E{{ episode|pad(2) }}
```

The template uses [Jinja2](https://jinja.palletsprojects.com/) syntax. AB renders it in a sandbox. Variables:

| Variable | Meaning | Example |
| --- | --- | --- |
| `title` | Title that AB parses from the file name | `Frieren` |
| `bangumi_name` | Name of the series folder | `Frieren (2023)` |
| `season` | Season, from the Season folder. It includes the season offset | `1` |
| `episode` | Episode. It includes the episode offset. Half episodes keep the decimal | `5`, `12.5` |
| `episode_type` | `episode`, `movie` or `special` | `episode` |
| `group` | Release group. It can be empty | `ANi` |
| `kind` | `media` (video) or `subtitle` | `media` |
| `language` | Subtitle language. It is empty for videos | `zh` |

The filter `pad(n)` adds zeros to the integer part of a number until it has n digits. If you do not give n, n is 2. The decimal part does not change. `{{ episode|pad(3) }}` gives `005`. `{{ 12.5|pad(2) }}` gives `12.5`.

- The template makes only the base of the file name. AB adds the extension. For subtitles, AB adds `.<language>` before the extension, for example `.zh.ass`.
- The template does not handle movies in a special way. To name movies differently, use `episode_type`, for example `{% if episode_type == "movie" %}{{ bangumi_name }}{% else %}…{% endif %}`. The check at save time renders only one sample episode. An error in a branch that the sample does not use shows only when AB renames a file.

Example: `[{{ group }}] {{ bangumi_name }} - {{ episode|pad(2) }}` → `[ANi] Frieren (2023) - 05.mkv`
:::

### Template errors

- **When you save**: AB renders the template once with a sample file. If the syntax is incorrect, a variable does not exist, or the result is not a valid file name, AB does not save the template. The old template stays.
- **When AB renames**: if a file does not render, the result is empty, or the result contains `/`, `\` or a control character, the file **keeps its name**. AB sends a "Files kept their names" notification. AB sends it one time for each torrent and reason while AB runs. AB does not add the `ab:renamed` tag to the torrent. After you correct the template, AB tries again in the next round. **AB does not use `pn` as a fallback.**
- **When you edit `config.json` manually**: if the saved template is not valid, the full `rename` plugin does not load. Then `pn`, `advance` and `template` are not available, and AB handles every series as `none`. The plugin card shows the error.

::: warning
A change of rename method (or of the template) applies only to torrents that AB organizes after the change. AB does not rename torrents that it organized before (torrents with the `ab:renamed` tag).
:::

For the `config.json` keys, see [Bangumi Manager](../config/manager.md).

## Collection Renaming

AB supports renaming collections. Collection renaming requires:
- Episodes are in the collection's first-level directory
- Episode numbers can be parsed from file names

AB can also rename subtitle files in the first-level directory.

After renaming, episodes and directories are placed in the `Season` folder.

Renamed collections are moved and categorized under `BangumiCollection`.

## Episode Offset

Since v3.2, AB supports episode offset for renaming. This is useful when:
- RSS shows different episode numbers than expected (e.g., S2E01 should be S1E29)
- Anime has "virtual seasons" due to broadcast gaps

When an offset is configured for a bangumi, AB automatically applies it during renaming:

```
Original: S02E01.mkv
With offset (season: -1, episode: +28): S01E29.mkv
```

To configure offset:
1. Click on the anime poster
2. Open Advanced Settings
3. Set Season Offset and/or Episode Offset values
4. Or use "Auto Detect" to let AB suggest the correct offset

See [Bangumi Management](./bangumi.md#episode-offset-auto-detection) for more details on auto-detection.

## After Renaming

After AB renames a torrent, it publishes a "torrent organized" event. AB also publishes this event when the rename method is `none`. Built-in plugins can then do more work on the files:

- [Hard Links to a Media Library](./hardlink.md): links the organized files into a different folder. The torrent continues to seed from the download folder.
- `media-server-refresh`: asks Jellyfin, Emby or Plex to refresh the library. See [Bangumi Manager](../config/manager.md).
