# Extension points

All imports come from `ab_sdk`. Constants live in `ab_sdk.points`.

## Providers

### downloader (`points.DOWNLOADER`)
```python
from ab_sdk.downloader import AddResult, DownloaderCapabilities, DownloaderConnection
```
- Factory is called with `DownloaderConnection(host, username, password, ssl, instance_id)`; return a client object. `instance_id` is the user-assigned instance id; key any local state by it, since two instances of the same type can coexist. Provider `id` is the instance type the user picks (`plugins.instances[].provider`).
- Minimum (`CoreDownloaderClient`): class attribute `capabilities = DownloaderCapabilities(can_query, can_rename, can_manage, can_rss_rules)`, `async auth(retry=3) -> bool`, `async logout()`, `async add_torrents(torrent_urls, torrent_files, save_path, category, tags=None) -> AddResult` (`ADDED` / `DUPLICATE` / `FAILED`).
- A declared capability requires its methods: `can_query` -> `torrents_info`, `torrent_exists`, `torrents_files`; `can_rename` -> `torrents_rename_file` (returns `RenameResult`); `can_manage` -> delete/pause/resume/move/category/tag methods. Undeclared operations are skipped and logged.
- Test: subclass `DownloaderContract`; set `behavioral = True` only when `create()` returns a client with a working backend or stub.

### notifier (`points.NOTIFIER`)
```python
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings
```
- `NotificationMessage(kind="episode"|"event", title, body, official_title, season, episode, poster_url)`.
- `NotifierSettings(template, extra)`. Put credentials in the plugin `config_model`, not in channel entries.
- Non-ASCII header values: pass `bytes` to httpx (`str` headers must be ASCII).
- Test: `NotifierContract`; implement `create_failing()` for the backend-refusal case.

### llm_provider (`points.LLM_PROVIDER`)
`ab_sdk.llm.LLMProviderAdapter` subclass with `info = ProviderInfo(id=..., display_name=..., auth_kind="api_key"|"oauth"|"device_code", ...)`. `@provider(..., id=)` must equal `info.id`. Raise `AuthExpiredError` when credentials are dead and refresh failed.

### search_site (`points.SEARCH_SITE`)
`SearchSite(url="https://x/rss?q=%s", parser="tmdb"|"mikan")`. Exactly one `%s`. User-defined site of the same name wins. Test: `SearchSiteContract`.

### scheduled_task (`points.SCHEDULED_TASK`)
`ScheduledTask(run, interval, initial_delay=0.0, enabled=None)`. `interval` and `enabled` may be callables re-read each round. Interval counts from the end of the previous run.

### metadata_provider (`points.METADATA_PROVIDER`)
Object with `async enrich(MetadataRequest) -> Metadata | None`. `MetadataRequest(kind, torrent, language, episode_type, current)`; return `replace(request.current, ...)`. The id appears in the subscription "parser" list.

### rename_strategy (`points.RENAME_STRATEGY`)
```python
from ab_sdk.rename import RenameInput, RenameSkipped, pad
```
- `RenameInput(kind, media_path, title, bangumi_name, season, episode, suffix, episode_type, language, group)`.
- Return the new relative path inside the torrent (add suffix and subtitle `.language` yourself). Return `f.media_path` for "no rename". `pad(9.5) == "09.5"`: keep half-episode fractions.
- `RenameSkipped(reason)`: file keeps its name, user is notified, not a breaker failure. Other exceptions, empty or non-str results count as failures.
- User picks the id at `plugins.slots.rename_strategy`; unregistered id acts as `none`. Test: `RenameStrategyContract` (override `samples()` for narrow strategies).

### media_files / conflict_policy
- `MediaFiles.classify(path) -> "media"|"subtitle"|"ignore"`; slot `plugins.slots.media_files`, default `default`.
- `ConflictPolicy.decide(ConflictRequest(target_path, incoming, owners, strict_upgrade)) -> ConflictDecision(action, reason)`. `replace` deletes the old task and files; the host runs it only for a single owner, single-file torrents and complete identities. Slot `plugins.slots.conflict_policy`, default `hold`.

### api_router (`points.API_ROUTER`)
Return `fastapi.APIRouter`. Mounted at `/api/v1/plugins/<id>/`. Always login-protected. `HTTPException` passes through; other exceptions give 500 and count as failures. Not in `/docs`.

### mcp_tool / mcp_resource
`McpTool(description, handler(args)->json, input_schema, timeout=60)`; public name `<plugin-id>__<id>`. `McpResource(name, handler()->str|json, description, mime_type)`; URI `autobangumi://plugins/<plugin-id>/<id>`.

## Hooks

- `torrent.filter`: `check(torrent: TorrentInfo, release: Release | None, bangumi: BangumiInfo) -> Verdict` (`Verdict.ok()` / `Verdict.reject(reason)`; bool also works).
- `title.parsed`: `fix(release)`; readable fields `raw, title_en, title_zh, title_jp, group, season, episode, resolution, source, subtitle, year`.
- `torrent.adding`: `adjust(AddRequest(bangumi, torrents, save_path, category, tags)) -> AddRequest | None`. Keep the `<name>/Season N` save-path shape; keep category `Bangumi` or AB stops organizing the torrent; the `ab:<id>` tag is restored if removed.
- `http.request`: `adjust(HttpRequest(method, url, headers))`; only header changes apply. Called for every GET: keep it cheap, no network inside.
- `message_template`: `(RenderedMessage(title, body), event, channel) -> RenderedMessage | None`; external push only; "new episode" notices are not covered.

## Events

`@subscribe(kind)` handlers get the event dataclass. System kinds: `rss_failure`, `download_failure`, `offset_review`, `downloader_unavailable`, `update_available`, `update_applied`, `update_failed`, `llm_auth_failure`, `llm_plugin_install_failed`, `rename_conflict`, `rename_skipped`, `plugin.loaded`, `plugin.disabled`. Organize kinds: `file.renamed` (`bangumi_id, old_path, new_path, file_kind, downloader_id`), `torrent.organized` (`torrent_hash, bangumi_id, files: tuple[OrganizedFile(path, kind)], downloader_id`).

Custom event:
```python
@dataclass(frozen=True, slots=True)
class Done(Event):          # SystemEvent for a notifiable event (add describe())
    kind: ClassVar[str] = "my-plugin.done"
    count: int
```
Publish with `self.ctx.bus.publish(Done(count=1))`.
