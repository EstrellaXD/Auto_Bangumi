# Example Plugins

The examples are in [`examples/plugins/`](https://github.com/EstrellaXD/Auto_Bangumi/tree/main/examples/plugins) of the repository. They are not in the Docker image. Each example has its own README and tests. CI runs them one by one.

| Example | What it shows |
| --- | --- |
| `webhook-on-event` | `@subscribe("*")`, a config form, `secret_field`. Sends selected events as a POST to a URL, with an optional HMAC signature |
| `custom-rss-site` | A `search_site` Provider and an `http.request` hook. Adds a Cookie to the requests of a private site. `SearchSiteContract` |
| `template-rename` | A `rename_strategy` Provider with a file-name template that has its own filters. `RenameSkipped`. `RenameStrategyContract` |
| `nfo-writer` | Subscribes to `torrent.organized` and writes an `.nfo` next to each media file. Path mapping. Idempotent |
| `ntfy-notifier` | A `notifier` Provider. Returns `False` when the backend refuses. `NotifierContract` |
| `manual-pick` | The frontend slot `bangumi.detail.tab`, plugin routes, plugin KV, events |

## Install an example

```bash
cp -r examples/plugins/ntfy-notifier config/plugins/local/
```

Turn on "Allow unsigned plugins" in Settings → Plugins, then enable the plugin.

## Run the tests of an example

```bash
cd examples/plugins/ntfy-notifier && uv run pytest
# or run all examples (in the repository root):
scripts/test_example_plugins.sh
```

You do not need a plugin to refresh a Jellyfin, Emby or Plex library. The built-in plugin `media-server-refresh` does it.
