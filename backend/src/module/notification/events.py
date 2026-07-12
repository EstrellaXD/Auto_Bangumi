"""非「新集数」通知的类型化事件负载。

刻意与 ``Notification``（module/models/bangumi.py，仅描述「新集数下载完成」）
分开：RSS 订阅失败、下载添加失败、偏移量待确认三类事件携带的字段与集数通知完全
无关，硬塞进 ``Notification`` 只会制造出没有意义的 season/episode 占位值。

每个事件同时服务两个消费方：

- 外部推送（Telegram/Bark 等）：``describe() -> (标题, 正文)`` 渲染中文文案；
- 站内通知中心：``kind``/``severity``/``once``/``dedup_key()``/``payload()``
  提供结构化字段，前端按 kind + payload 做多语言渲染，describe() 文案作为
  未知 kind 的兜底展示。``once=True`` 表示同 dedup_key 终生只入库一次
  （如"新版本可用"，已读后同一版本不再提醒）。
"""

from dataclasses import dataclass
from typing import ClassVar, Optional


@dataclass(slots=True, frozen=True)
class RssFailureEvent:
    """RSS 订阅连接状态从正常变为异常（仅状态翻转时触发一次，而非每个 tick）。"""

    kind: ClassVar[str] = "rss_failure"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    rss_name: str
    rss_url: str
    error: str

    def dedup_key(self) -> Optional[str]:
        return f"rss_failure:{self.rss_url}"

    def payload(self) -> dict:
        return {"rss_name": self.rss_name, "rss_url": self.rss_url, "error": self.error}

    def describe(self) -> tuple[str, str]:
        """返回该事件的默认 (标题, 正文)。"""
        return (
            "RSS 订阅连接异常",
            f"订阅：{self.rss_name}\n地址：{self.rss_url}\n错误：{self.error}",
        )


@dataclass(slots=True, frozen=True)
class DownloadFailureEvent:
    """匹配到的种子在（内置 HTTP 重试后）仍添加下载器失败。"""

    kind: ClassVar[str] = "download_failure"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    official_title: str
    torrent_name: str

    def dedup_key(self) -> Optional[str]:
        return f"download_failure:{self.official_title}"

    def payload(self) -> dict:
        return {
            "official_title": self.official_title,
            "torrent_name": self.torrent_name,
        }

    def describe(self) -> tuple[str, str]:
        return (
            "种子添加失败",
            f"番剧：{self.official_title}\n种子：{self.torrent_name}\n"
            "重试后仍添加失败，请检查下载器连接。",
        )


@dataclass(slots=True, frozen=True)
class OffsetReviewEvent:
    """番剧被标记为需要人工确认季度/集数偏移。"""

    kind: ClassVar[str] = "offset_review"
    severity: ClassVar[str] = "warning"
    once: ClassVar[bool] = False

    official_title: str
    reason: str

    def dedup_key(self) -> Optional[str]:
        return f"offset_review:{self.official_title}"

    def payload(self) -> dict:
        return {"official_title": self.official_title, "reason": self.reason}

    def describe(self) -> tuple[str, str]:
        return (
            "集数偏移待确认",
            f"番剧：{self.official_title}\n原因：{self.reason}\n请前往设置页确认偏移量。",
        )


@dataclass(slots=True, frozen=True)
class DownloaderUnavailableEvent:
    """下载器不可用：连不上、用户名/密码错误或 IP 被封禁。

    ``reason`` 只进 payload 不进 dedup_key——同一台下载器从 unreachable 翻转
    到 credentials 时合并为一条（内容以最新为准），不产生两行。
    """

    kind: ClassVar[str] = "downloader_unavailable"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    host: str
    reason: str  # unreachable | credentials | banned

    def dedup_key(self) -> Optional[str]:
        return f"downloader:{self.host}"

    def payload(self) -> dict:
        return {"host": self.host, "reason": self.reason}

    def describe(self) -> tuple[str, str]:
        details = {
            "credentials": "用户名或密码错误，请在设置中检查下载器凭据。",
            "banned": "IP 已被下载器封禁，请在下载器 WebUI 中解封或重启下载器。",
            "unreachable": "无法连接下载器，请检查地址、端口和网络。",
        }
        detail = details.get(self.reason, details["unreachable"])
        return ("下载器连接异常", f"下载器：{self.host}\n{detail}")


@dataclass(slots=True, frozen=True)
class UpdateAvailableEvent:
    """检查到可用的新版本。"""

    kind: ClassVar[str] = "update_available"
    severity: ClassVar[str] = "info"
    once: ClassVar[bool] = True

    current: str
    latest: str
    channel: str
    notes: str = ""

    def dedup_key(self) -> Optional[str]:
        return f"update_available:{self.latest}"

    def payload(self) -> dict:
        return {
            "current": self.current,
            "latest": self.latest,
            "channel": self.channel,
            "notes": self.notes,
        }

    def describe(self) -> tuple[str, str]:
        return (
            "发现新版本",
            f"当前版本：{self.current}\n最新版本：{self.latest}（{self.channel} 频道）\n"
            "可前往 设置 → 软件更新 升级。",
        )


@dataclass(slots=True, frozen=True)
class UpdateAppliedEvent:
    """更新应用结果（成功或失败）。每次结果都单独入库，不做去重。"""

    once: ClassVar[bool] = False

    version: str
    success: bool
    message: str = ""

    @property
    def kind(self) -> str:
        return "update_applied" if self.success else "update_failed"

    @property
    def severity(self) -> str:
        return "info" if self.success else "error"

    def dedup_key(self) -> Optional[str]:
        return None

    def payload(self) -> dict:
        return {"version": self.version, "message": self.message}

    def describe(self) -> tuple[str, str]:
        if self.success:
            return ("程序更新完成", f"已更新到 {self.version}，重启后生效。")
        return ("程序更新失败", f"版本：{self.version}\n原因：{self.message}")


@dataclass(slots=True, frozen=True)
class LLMAuthFailureEvent:
    """订阅类 LLM 提供商凭据失效（刷新失败），需要用户重新连接。"""

    kind: ClassVar[str] = "llm_auth_failure"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    provider_id: str
    account_label: str = ""
    message: str = ""

    def dedup_key(self) -> Optional[str]:
        return f"llm_auth:{self.provider_id}"

    def payload(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "account_label": self.account_label,
            "message": self.message,
        }

    def describe(self) -> tuple[str, str]:
        account = f"（{self.account_label}）" if self.account_label else ""
        return (
            "LLM 提供商凭据失效",
            f"提供商：{self.provider_id}{account}\n{self.message}\n"
            "请前往 设置 → LLM 解析器 重新连接。",
        )


@dataclass(slots=True, frozen=True)
class LLMPluginInstallFailedEvent:
    """LLM 提供商插件安装失败（下载/签名校验/兼容性）。"""

    kind: ClassVar[str] = "llm_plugin_install_failed"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    plugin_id: str
    version: str = ""
    message: str = ""

    def dedup_key(self) -> Optional[str]:
        return f"llm_plugin_install:{self.plugin_id}"

    def payload(self) -> dict:
        return {
            "plugin_id": self.plugin_id,
            "version": self.version,
            "message": self.message,
        }

    def describe(self) -> tuple[str, str]:
        return (
            "LLM 插件安装失败",
            f"插件：{self.plugin_id} {self.version}\n原因：{self.message}",
        )


@dataclass(slots=True, frozen=True)
class RenameConflictEvent:
    """A media rename reached a durable target-path conflict."""

    kind: ClassVar[str] = "rename_conflict"
    severity: ClassVar[str] = "warning"
    once: ClassVar[bool] = False

    task_id: str
    torrent_name: str
    target_path: str
    reason: str

    def dedup_key(self) -> Optional[str]:
        return f"rename_conflict:{self.task_id}:{self.target_path}"

    def payload(self) -> dict:
        return {
            "task_id": self.task_id,
            "torrent_name": self.torrent_name,
            "target_path": self.target_path,
            "reason": self.reason,
        }

    def describe(self) -> tuple[str, str]:
        return (
            "媒体文件重命名冲突",
            f"种子：{self.torrent_name}\n目标：{self.target_path}\n"
            f"原因：{self.reason}",
        )


# 除「新集数」以外的通知事件的联合类型。
SystemEvent = (
    RssFailureEvent
    | DownloadFailureEvent
    | OffsetReviewEvent
    | DownloaderUnavailableEvent
    | UpdateAvailableEvent
    | UpdateAppliedEvent
    | LLMAuthFailureEvent
    | LLMPluginInstallFailedEvent
    | RenameConflictEvent
)
