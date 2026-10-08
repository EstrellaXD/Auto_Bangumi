---
name: autobangumi-plugin
description: Write, test, pack and debug AutoBangumi (AB) 4.0 plugins with the ab_sdk Python SDK and the ab-plugin CLI. Use when the user asks to "write an AutoBangumi plugin", "add a downloader / notifier / search site / rename strategy / RSS site to AutoBangumi", "hook into AutoBangumi", mentions ab_sdk, ab-plugin, plugin.toml, @provider, @hook, @subscribe, secret_field, or wants a custom rename template, webhook on torrent.organized, nfo writer, private tracker Cookie, or a plugin web component for the AutoBangumi WebUI.
---

# AutoBangumi plugin authoring

AB plugins are Python packages (optional Web Component UI) that run inside the AB process. They import only `ab_sdk`, never `module.*`. SDK is 0.x during 4.0: pin `sdk = ">=0.5,<1"` in the manifest.

## Workflow

1. Pick the extension point (table below). If unsure, read `references/extension-points.md`.
2. Scaffold: `ab-plugin new <id> --kind rename|notifier|search` (ids: lowercase, digits, hyphens; `core` and `local` are reserved). For other points, copy the closest example from `examples/plugins/` in the AB repo.
3. Write the plugin: one `Plugin[Options]` subclass, `config_model = Options`, decorated methods.
4. Test first: `uv run pytest`. Provider points have contract suites in `ab_sdk.testing` (subclass, implement `create()`). Other behavior: `create_plugin(Cls, options)` plus `asyncio.run`.
5. `ab-plugin validate .` then `ab-plugin dev .` (links into `config/plugins/local/`, enables hot reload; restart AB once) then `ab-plugin pack .`.

Install the tooling from the GitHub release wheel (`autobangumi_sdk-<ver>-py3-none-any.whl`), not PyPI.

## Skeleton

```python
from pydantic import BaseModel, Field
from ab_sdk import Plugin, points, provider, hook, subscribe, secret_field

class Options(BaseModel):
    url: str = Field("", title="URL")             # title/description become the WebUI form labels
    token: str = secret_field(title="Token")      # password box; masked on read

class MyPlugin(Plugin[Options]):
    config_model = Options                         # self.config is a validated Options

    @provider(points.NOTIFIER, id="my-push")      # Provider: the thing the user selects by id
    def channel(self): ...

    @hook(points.TORRENT_FILTER, priority=50)     # Hook: runs in the AB pipeline
    def check(self, torrent, release, bangumi): ...

    @subscribe("torrent.organized", timeout=600)  # Event subscriber ("*" = all events)
    async def on_organized(self, event): ...
```

`self.ctx`: `plugin_id`, `config`, `log`, `kv` (async get/set/delete, JSON values), `data_dir`, `bus` (`publish`, `subscribe`).

## Extension points

| Point constant | Kind | Returns / signature |
| --- | --- | --- |
| `DOWNLOADER` | provider | `DownloaderFactory`: `(DownloaderConnection) -> client` with `capabilities`, `auth`, `logout`, `add_torrents` |
| `NOTIFIER` | provider | `NotifierFactory`: `(NotifierSettings) -> Notifier` (`send -> bool`, `test -> (bool, str)`) |
| `LLM_PROVIDER` | provider | `LLMProviderAdapter` subclass; id must equal `info.id` |
| `SEARCH_SITE` | provider | `SearchSite(url_with_%s, parser="tmdb"\|"mikan")` |
| `SCHEDULED_TASK` | provider | `ScheduledTask(run, interval, initial_delay, enabled)` |
| `METADATA_PROVIDER` | provider | object with `async enrich(MetadataRequest) -> Metadata \| None` |
| `RENAME_STRATEGY` | provider | object with `target_name(RenameInput) -> str`; raise `RenameSkipped` for bad input |
| `MEDIA_FILES` | provider | `classify(path) -> "media"\|"subtitle"\|"ignore"` |
| `CONFLICT_POLICY` | provider | `decide(ConflictRequest) -> ConflictDecision("hold"\|"replace", reason)` |
| `API_ROUTER` | provider | `fastapi.APIRouter`, mounted at `/api/v1/plugins/<id>/`, login required |
| `MCP_TOOL` / `MCP_RESOURCE` | provider | `McpTool` / `McpResource` |
| `TORRENT_FILTER` | filter hook | `(torrent, release, bangumi) -> Verdict` |
| `TITLE_PARSED` | transform hook | `(release) -> release \| None` |
| `TORRENT_ADDING` | transform hook | `(AddRequest) -> AddRequest \| None` |
| `HTTP_REQUEST` | transform hook | `(HttpRequest) -> HttpRequest \| None` (headers only) |
| `MESSAGE_TEMPLATE` | transform hook | `(RenderedMessage, event, channel) -> RenderedMessage \| None` |

Details, imports and field lists: `references/extension-points.md`.

## Rules that prevent most bugs

- Hooks get frozen snapshots. Return `dataclasses.replace(obj, ...)`; return `None` for "no change". A wrong return type counts as a failure.
- Five consecutive failures trip the circuit breaker and disable the plugin. `RenameSkipped` is not a failure. Never fall back to another naming method after a failure.
- Filter hooks fail open (a crash accepts the torrent). Notifier `send` returns `False` on a backend refusal; it does not raise.
- Events: plugin event `kind` must start with `<plugin-id>.`. Subclass `SystemEvent` to make a notifiable event. `torrent.organized` is delivered at least once: make handlers idempotent. Event paths are downloader-side paths; map them (`path_from` / `path_to` options) before touching the disk.
- Blocking work (file IO, copies) goes in `asyncio.to_thread`; `target_name` is sync with no timeout, so no IO there.
- Validate config deeply in `field_validator` so bad values give HTTP 422 at save time.
- No native extensions (`.so`, `.pyd`, `.dylib`, `.dll`). Third-party pure-Python deps go in `vendor/`; AB does not run pip for catalog or local plugins.
- Plugin routes cannot use the paths `web/`, `install`, `catalog`.
- Local and pip plugins are unsigned: the user must turn on "Allow unsigned plugins". Only maintainers sign the catalog (`scripts/build_plugin_catalog.py`).

## References

- `references/extension-points.md`: imports, dataclass fields and gotchas per extension point.
- `references/testing.md`: contract suites, `create_plugin`, `ab-plugin` commands, the manifest.
- `references/frontend.md`: `[[plugin.ui]]`, slots, `AbHost`, CSP, build template.
- Examples (in the AB repo): `examples/plugins/` has `webhook-on-event`, `custom-rss-site`, `template-rename`, `nfo-writer`, `ntfy-notifier`, `manual-pick`.
