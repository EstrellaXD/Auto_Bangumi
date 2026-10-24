# Rename Strategy (rename_strategy)

After a download completes, AB calls the Provider that the setting "rename method" (`plugins.slots.rename_strategy`) selects, for each media file and subtitle in the torrent. The host has only `none` (keep the name). The built-in plugin `rename` provides `pn`, `advance` and `template`. The `id` that a plugin registers appears in the list in Settings → Series management → Rename method.

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.rename import RenameInput, RenameSkipped, pad


class JellyfinStyle:
    def target_name(self, f: RenameInput) -> str:
        language = f".{f.language}" if f.kind == "subtitle" else ""
        if f.episode_type == "movie":
            return f"{f.bangumi_name}{language}{f.suffix}"
        if not f.bangumi_name:
            raise RenameSkipped("the series folder name is missing")
        return f"{f.bangumi_name} - S{pad(f.season)}E{pad(f.episode)}{language}{f.suffix}"


class MyRename(Plugin):
    @provider(points.RENAME_STRATEGY, id="jellyfin-style")
    def jellyfin(self):
        return JellyfinStyle()
```

## RenameInput

A frozen snapshot.

| Field | Description |
| --- | --- |
| `kind` | `media` or `subtitle` (subtitles have no separate method; use `kind`) |
| `media_path` | The original relative path in the torrent |
| `title` | The title parsed from the file name |
| `bangumi_name` | The series folder name of the save directory (`Title (Year)` for a movie) |
| `season`, `episode` | Season and episode. `episode` already has the episode offset |
| `suffix` | The extension with the dot, for example `.mkv` |
| `episode_type` | `episode`, `movie` or `special` |
| `language` | The subtitle language, for example `zh`, `zh-tw` |
| `group` | The release group; can be `None` |

`title` and `bangumi_name` come from file names and folder names that already exist on disk. Each is one path component. AB does not remove reserved characters from them.

## Return values and errors

- Return the new relative path in the torrent. Usually this is only a file name. The strategy adds the extension and the subtitle language. Return `f.media_path` for no rename.
- `pad(n, width=2)` pads with zeros and keeps the fraction: `pad(9.5) == "09.5"`. Half episodes such as recap episodes must keep the fraction. Otherwise they overwrite the whole episode of the same season.
- Raise `RenameSkipped(reason)`: the file keeps its name, the torrent does not get the "renamed" tag, and AB sends one `rename_skipped` notification per torrent with the reason. AB retries in the next round after you fix the problem. This exception means that the input or the configuration has a problem. It does not count toward the breaker. **Do not fall back to another naming method on failure.**
- Another exception, an empty string or a value that is not a string: the file also keeps its name and AB sends a notification, and the failure counts toward the breaker.
- `target_name` is a synchronous call with no timeout. Do not do network or disk IO in it.
- If the `id` in the settings is not registered (the plugin is disabled or tripped), AB writes one log line and acts as `none`.

## Tests

```python
from ab_sdk.testing import RenameStrategyContract, create_plugin

class TestStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin(MyRename)
        return plugin.jellyfin()
```

The suite checks: a non-empty relative path, no `..`, the suffix is kept, the result is deterministic. If your strategy fits only some inputs, override `samples()`.

Example: `examples/plugins/template-rename` (a template with its own filters).
