# Events

An event is a frozen dataclass. The class variable `kind` is the event name. The host and the plugins share one event bus.

```python
from ab_sdk import subscribe
from ab_sdk.events import RssFailureEvent

@subscribe("rss_failure")
async def on_rss_failure(self, event: RssFailureEvent):
    self.ctx.log.warning("Subscription %s failed: %s", event.rss_name, event.error)
```

- Subscribers run asynchronously in their own queue, in publish order. A failure or a timeout does not affect the publisher, and it counts toward the plugin breaker. The default timeout is 30 seconds. For long operations such as copying large files, use `@subscribe(kind, timeout=600)`.
- `"*"` subscribes to all events.
- Publish with `self.ctx.bus.publish(event)`. The `kind` of a plugin event must start with `<plugin id>.`. This prevents a clash with host events.
- A frontend component subscribes to the same bus with `host.events.on(kind, callback)`. The callback gets the event fields (see [Frontend slots](/en/dev/plugins/frontend-slots)).

## System events

The events that AB sends to the notification center are all subclasses of `ab_sdk.events.SystemEvent`. They have `severity`, `payload()`, `describe()` (default Chinese title and body) and `i18n()` (the frontend i18n key and parameters). AB first writes them to the notification center, then publishes them on the event bus, then pushes them to external channels. The "notification" switch affects only the external push. Plugins always receive the events.

| kind | Event class | When AB publishes it |
| --- | --- | --- |
| `rss_failure` | `RssFailureEvent` | An RSS subscription changes from normal to a connection failure |
| `download_failure` | `DownloadFailureEvent` | A torrent still fails to add after retries |
| `offset_review` | `OffsetReviewEvent` | The season or episode offset of a series needs a manual check |
| `downloader_unavailable` | `DownloaderUnavailableEvent` | The downloader is unreachable, the credentials are wrong or the IP is banned; once per instance when it changes from available to unavailable |
| `update_available` | `UpdateAvailableEvent` | A new version is found |
| `update_applied` / `update_failed` | `UpdateAppliedEvent` | An online update succeeds / fails |
| `llm_auth_failure` | `LLMAuthFailureEvent` | The credentials of a subscription-type LLM provider are no longer valid |
| `llm_plugin_install_failed` | `LLMPluginInstallFailedEvent` | The installation of an LLM plugin fails |
| `rename_conflict` | `RenameConflictEvent` | A media file rename meets a target path conflict |
| `rename_skipped` | `RenameSkippedEvent` | The rename strategy cannot name a file; the file keeps its name |
| `plugin.loaded` | `PluginLoaded` | A plugin loads successfully |
| `plugin.disabled` | `PluginDisabled` | A plugin fails to load or the breaker trips |

The `kind` of a system event keeps the 3.x value (the notification center stores and translates by it). So it has no `.` prefix.

## Organize events

| kind | Event class | Fields | When AB publishes it |
| --- | --- | --- | --- |
| `file.renamed` | `FileRenamed` | `bangumi_id`, `old_path`, `new_path`, `file_kind`, `downloader_id` | A file is renamed (including a rename after a version replacement) |
| `torrent.organized` | `TorrentOrganized` | `torrent_hash`, `bangumi_id`, `files` (a tuple of `OrganizedFile(path, kind)`), `downloader_id` | A torrent is organized. AB also publishes it when the rename strategy is `none`; `files` then holds the original paths |

- Paths are absolute paths **as the downloader sees them**, joined with `/` (a `\` from a Windows downloader is also changed to `/`). If AB and the downloader see different directories (for example, they run in different containers), the subscriber must map the paths.
- `bangumi_id` comes from the `ab:<id>` tag of the torrent. An old torrent can have `None`. `downloader_id` is the id of the downloader instance that holds the torrent. Different instances can have different path views.
- `torrent.organized` has **at-least-once** delivery. AB publishes it again after each restart for torrents without the "renamed" tag (for example, when the rename strategy is `none`). Subscribers must be idempotent.
- These two events go to the event bus only. They do not go to the notification center.

## Custom events

Inherit `Event` for a normal event. Inherit `SystemEvent` for a notifiable event. After you publish it, it takes the same path as a host event: the notification center (the frontend shows the title and body of `describe()` if it has no translation), the event bus and the external channels. Events with the same `dedup_key()` merge into one entry in the notification center.

```python
from dataclasses import dataclass
from typing import ClassVar
from ab_sdk.events import SystemEvent

@dataclass(frozen=True, slots=True)
class SyncFailed(SystemEvent):
    kind: ClassVar[str] = "my-plugin.sync_failed"
    severity: ClassVar[str] = "warning"
    reason: str

    def describe(self) -> tuple[str, str]:
        return ("Sync failed", self.reason)
```

The built-in `hardlink` plugin sends its `hardlink.failed` event in this way.
