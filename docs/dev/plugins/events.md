# 事件

事件是冻结的 dataclass，类变量 `kind` 是事件名。宿主和插件共用一条事件总线。

```python
from ab_sdk import subscribe
from ab_sdk.events import RssFailureEvent

@subscribe("rss_failure")
async def on_rss_failure(self, event: RssFailureEvent):
    self.ctx.log.warning("订阅 %s 失败：%s", event.rss_name, event.error)
```

- 订阅者在独立队列中按发布顺序异步执行。失败或超时不影响发布方，并计入插件熔断。默认超时 30 秒；复制大文件等耗时操作用 `@subscribe(kind, timeout=600)`。
- `"*"` 订阅全部事件。
- 用 `self.ctx.bus.publish(event)` 发布。插件事件的 `kind` 必须以 `<插件 id>.` 开头，避免与宿主事件冲突。
- 前端组件用 `host.events.on(kind, callback)` 订阅同一条总线，回调收到事件的字段（见 [前端挂载点](/dev/plugins/frontend-slots)）。

## 系统事件

AB 发出的、会进入通知中心的事件都是 `ab_sdk.events.SystemEvent` 的子类，带有 `severity`、`payload()`、`describe()`（默认中文标题与正文）和 `i18n()`（前端 i18n key 与参数）。它们先写入通知中心，再发布到事件总线，最后推送到外部通知渠道。关闭「通知」开关只影响外部推送，不影响插件收到事件。

| kind | 事件类 | 何时发布 |
| --- | --- | --- |
| `rss_failure` | `RssFailureEvent` | RSS 订阅从正常变为连接异常 |
| `download_failure` | `DownloadFailureEvent` | 种子重试后仍添加失败 |
| `offset_review` | `OffsetReviewEvent` | 番剧的季度 / 集数偏移需要人工确认 |
| `downloader_unavailable` | `DownloaderUnavailableEvent` | 下载器连不上、凭据错误或 IP 被封；每个实例从可用变为不可用时发布一次 |
| `update_available` | `UpdateAvailableEvent` | 检查到新版本 |
| `update_applied` / `update_failed` | `UpdateAppliedEvent` | 在线更新成功 / 失败 |
| `llm_auth_failure` | `LLMAuthFailureEvent` | 订阅类 LLM 提供商凭据失效 |
| `llm_plugin_install_failed` | `LLMPluginInstallFailedEvent` | LLM 插件安装失败 |
| `rename_conflict` | `RenameConflictEvent` | 媒体文件重命名遇到目标路径冲突 |
| `rename_skipped` | `RenameSkippedEvent` | 重命名方式无法为文件给出名字，文件保留原名 |
| `plugin.loaded` | `PluginLoaded` | 插件加载成功 |
| `plugin.disabled` | `PluginDisabled` | 插件加载失败或被熔断 |

系统事件的 `kind` 沿用 3.x 的取值（通知中心按它存储和翻译），因此不带 `.` 前缀。

## 整理事件

| kind | 事件类 | 字段 | 何时发布 |
| --- | --- | --- | --- |
| `file.renamed` | `FileRenamed` | `bangumi_id`、`old_path`、`new_path`、`file_kind`、`downloader_id` | 一个文件被实际重命名（含版本替换后的改名） |
| `torrent.organized` | `TorrentOrganized` | `torrent_hash`、`bangumi_id`、`files`（`OrganizedFile(path, kind)` 元组）、`downloader_id` | 一个种子整理完成；重命名方式为 `none` 时同样发布，`files` 为原路径。选中的重命名方式未登记（插件停用或被熔断）时不发布 |

- 路径是**下载器视角**的绝对路径，以 `/` 拼接（Windows 下载器的 `\` 也统一为 `/`）。AB 与下载器看到的目录不同（如分别运行在不同容器）时，订阅者要自己做路径映射。
- `bangumi_id` 来自种子的 `ab:<id>` 标签，旧种子可能为 `None`。`downloader_id` 是种子所在下载器实例的 id；多个实例的路径视角可能不同。
- `torrent.organized` 的投递是**至少一次**：下载器中已整理的种子（包括已打「已重命名」标签的）在每次 AB 重启后会再发布一次。订阅者必须幂等。
- 这两个事件只发布到事件总线，不进入通知中心。

## 自定义事件

继承 `Event` 定义一般事件。继承 `SystemEvent` 定义可通知事件：发布后它与宿主事件走同一条路径，即写入通知中心（前端没有对应翻译时显示 `describe()` 的标题与正文）、发布到事件总线、推送到外部渠道。`dedup_key()` 相同的事件在通知中心合并为一条。

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
        return ("同步失败", self.reason)
```

内置插件 `hardlink` 的 `hardlink.failed` 就是这样发出的。
