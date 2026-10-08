"""事件基类与宿主发布的通用事件。

事件是冻结 dataclass，``kind`` 为类变量。插件可以定义并发布自己的事件，
``kind`` 须以 ``<plugin-id>.`` 为前缀，避免与宿主事件冲突。
"""

from dataclasses import dataclass
from typing import ClassVar

from .rename import FileKind


@dataclass(frozen=True, slots=True)
class Event:
    kind: ClassVar[str] = "event"


@dataclass(frozen=True, slots=True)
class PluginLoaded(Event):
    kind: ClassVar[str] = "plugin.loaded"
    plugin_id: str
    version: str


@dataclass(frozen=True, slots=True)
class PluginDisabled(Event):
    """插件加载失败，或运行中连续失败被熔断后发布。"""

    kind: ClassVar[str] = "plugin.disabled"
    plugin_id: str
    reason: str


# --- P5：系统事件 -------------------------------------------------------------
#
# 以下事件由宿主经 ``NotificationManager.send_event`` 发出：先写入站内通知中心，
# 再发布到事件总线（插件可 ``@subscribe(kind)``），最后推送到外部通知渠道。
# ``kind`` 沿用 3.x 的取值（站内通知中心按 kind 存储与翻译），不带 ``.`` 前缀。


@dataclass(frozen=True, slots=True)
class SystemEvent(Event):
    """可通知事件的基类：同时服务外部推送、站内通知中心与事件总线。

    - ``describe()`` 返回默认中文 (标题, 正文)，用于外部推送与通知中心兜底展示；
    - ``i18n()`` 返回 (i18n key, 参数)，前端据此按当前语言渲染，key 形如
      ``notifications.kind.<kind>``，其下有 ``title`` / ``body`` 两条文案；
    - ``severity`` 为 ``info`` / ``warning`` / ``error``；
    - ``once=True`` 表示同 ``dedup_key()`` 终生只入库一次（如「新版本可用」）。

    插件也可以继承它定义自己的可通知事件（``kind`` 须以 ``<plugin-id>.`` 开头）。
    """

    kind: ClassVar[str] = "system"
    severity: ClassVar[str] = "info"
    once: ClassVar[bool] = False

    def dedup_key(self) -> str | None:
        """通知中心的去重键；None 表示每次都新建一条。"""
        return None

    def payload(self) -> dict:
        """结构化字段，入库为 JSON，也是 i18n 文案的插值参数。"""
        from dataclasses import fields

        return {f.name: getattr(self, f.name) for f in fields(self)}

    def describe(self) -> tuple[str, str]:
        """默认 (标题, 正文)。"""
        return (self.kind, "")

    def i18n(self) -> tuple[str, dict]:
        """(i18n key, 插值参数)。默认 key 为 ``notifications.kind.<kind>``。"""
        return f"notifications.kind.{self.kind}", self.payload()


@dataclass(frozen=True, slots=True)
class RssFailureEvent(SystemEvent):
    """RSS 订阅连接状态从正常变为异常（仅状态翻转时触发一次，而非每个 tick）。"""

    kind: ClassVar[str] = "rss_failure"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    rss_name: str
    rss_url: str
    error: str

    def dedup_key(self) -> str | None:
        return f"rss_failure:{self.rss_url}"

    def payload(self) -> dict:
        return {"rss_name": self.rss_name, "rss_url": self.rss_url, "error": self.error}

    def describe(self) -> tuple[str, str]:
        """返回该事件的默认 (标题, 正文)。"""
        return (
            "RSS 订阅连接异常",
            f"订阅：{self.rss_name}\n地址：{self.rss_url}\n错误：{self.error}",
        )


@dataclass(frozen=True, slots=True)
class DownloadFailureEvent(SystemEvent):
    """匹配到的种子在（内置 HTTP 重试后）仍添加下载器失败。"""

    kind: ClassVar[str] = "download_failure"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    official_title: str
    torrent_name: str

    def dedup_key(self) -> str | None:
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


@dataclass(frozen=True, slots=True)
class OffsetReviewEvent(SystemEvent):
    """番剧被标记为需要人工确认季度/集数偏移。"""

    kind: ClassVar[str] = "offset_review"
    severity: ClassVar[str] = "warning"
    once: ClassVar[bool] = False

    official_title: str
    reason: str

    def dedup_key(self) -> str | None:
        return f"offset_review:{self.official_title}"

    def payload(self) -> dict:
        return {"official_title": self.official_title, "reason": self.reason}

    def describe(self) -> tuple[str, str]:
        return (
            "集数偏移待确认",
            f"番剧：{self.official_title}\n原因：{self.reason}\n请前往设置页确认偏移量。",
        )


@dataclass(frozen=True, slots=True)
class DownloaderUnavailableEvent(SystemEvent):
    """下载器不可用：连不上、用户名/密码错误或 IP 被封禁。

    ``reason`` 只进 payload 不进 dedup_key——同一台下载器从 unreachable 翻转
    到 credentials 时合并为一条（内容以最新为准），不产生两行。
    """

    kind: ClassVar[str] = "downloader_unavailable"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    host: str
    reason: str  # unreachable | credentials | banned
    instance_id: str = "default"  # 下载器实例 id（plugins.instances）

    def dedup_key(self) -> str | None:
        return f"downloader:{self.instance_id}"

    def payload(self) -> dict:
        return {"host": self.host, "reason": self.reason, "instance": self.instance_id}

    def describe(self) -> tuple[str, str]:
        details = {
            "credentials": "用户名或密码错误，请在设置中检查下载器凭据。",
            "banned": "IP 已被下载器封禁，请在下载器 WebUI 中解封或重启下载器。",
            "unreachable": "无法连接下载器，请检查地址、端口和网络。",
        }
        detail = details.get(self.reason, details["unreachable"])
        return (
            "下载器连接异常",
            f"下载器：{self.instance_id}（{self.host}）\n{detail}",
        )


@dataclass(frozen=True, slots=True)
class UpdateAvailableEvent(SystemEvent):
    """检查到可用的新版本。"""

    kind: ClassVar[str] = "update_available"
    severity: ClassVar[str] = "info"
    once: ClassVar[bool] = True

    current: str
    latest: str
    channel: str
    notes: str = ""

    def dedup_key(self) -> str | None:
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


@dataclass(frozen=True, slots=True)
class UpdateAppliedEvent(SystemEvent):
    """更新应用结果（成功或失败）。每次结果都单独入库，不做去重。"""

    once: ClassVar[bool] = False

    version: str
    success: bool
    message: str = ""

    # kind / severity 随结果变化，因此用属性覆盖基类的类变量
    @property
    def kind(self) -> str:  # type: ignore[override]
        return "update_applied" if self.success else "update_failed"

    @property
    def severity(self) -> str:  # type: ignore[override]
        return "info" if self.success else "error"

    def dedup_key(self) -> str | None:
        return None

    def payload(self) -> dict:
        return {"version": self.version, "message": self.message}

    def describe(self) -> tuple[str, str]:
        if self.success:
            return ("程序更新完成", f"已更新到 {self.version}，重启后生效。")
        return ("程序更新失败", f"版本：{self.version}\n原因：{self.message}")


@dataclass(frozen=True, slots=True)
class LLMAuthFailureEvent(SystemEvent):
    """订阅类 LLM 提供商凭据失效（刷新失败），需要用户重新连接。"""

    kind: ClassVar[str] = "llm_auth_failure"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    provider_id: str
    account_label: str = ""
    message: str = ""

    def dedup_key(self) -> str | None:
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


@dataclass(frozen=True, slots=True)
class LLMPluginInstallFailedEvent(SystemEvent):
    """LLM 提供商插件安装失败（下载/签名校验/兼容性）。"""

    kind: ClassVar[str] = "llm_plugin_install_failed"
    severity: ClassVar[str] = "error"
    once: ClassVar[bool] = False

    plugin_id: str
    version: str = ""
    message: str = ""

    def dedup_key(self) -> str | None:
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


@dataclass(frozen=True, slots=True)
class RenameConflictEvent(SystemEvent):
    """媒体文件重命名遇到无法自动解决的目标路径冲突。"""

    kind: ClassVar[str] = "rename_conflict"
    severity: ClassVar[str] = "warning"
    once: ClassVar[bool] = False

    task_id: str
    torrent_name: str
    target_path: str
    reason: str

    def dedup_key(self) -> str | None:
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


@dataclass(frozen=True, slots=True)
class RenameSkippedEvent(SystemEvent):
    """重命名策略无法为种子中的文件给出名字（如模板渲染失败），文件保留原名。

    同一种子、同一原因每个进程只通知一次；修正配置后下一轮会自动重试。
    """

    kind: ClassVar[str] = "rename_skipped"
    severity: ClassVar[str] = "warning"
    once: ClassVar[bool] = False

    task_id: str
    torrent_name: str
    strategy: str
    reason: str

    def dedup_key(self) -> str | None:
        return f"rename_skipped:{self.task_id}"

    def payload(self) -> dict:
        return {
            "task_id": self.task_id,
            "torrent_name": self.torrent_name,
            "strategy": self.strategy,
            "reason": self.reason,
        }

    def describe(self) -> tuple[str, str]:
        return (
            "文件未重命名",
            f"种子：{self.torrent_name}\n重命名方式：{self.strategy}\n"
            f"原因：{self.reason}\n文件已保留原名，修正后会自动重试。",
        )


# --- P4：organize 流水线事件（只发布到事件总线，不进通知中心） -------------------
#
# 路径均为下载器视角的绝对路径：保存目录与种子内相对路径以 "/" 拼接
# （Windows 下载器的 "\" 也统一为 "/"）。AutoBangumi 与下载器不在同一文件系统
# 视图时（容器挂载不同），订阅者需要自行做路径映射。


@dataclass(frozen=True, slots=True)
class FileRenamed(Event):
    """下载器中的一个文件被重命名到规范名（正片或字幕）。"""

    kind: ClassVar[str] = "file.renamed"
    bangumi_id: int | None  # 来自种子的 ab:<id> 标签；旧种子可能没有
    old_path: str
    new_path: str
    file_kind: FileKind
    downloader_id: str = "default"


@dataclass(frozen=True, slots=True)
class OrganizedFile:
    path: str
    kind: FileKind


@dataclass(frozen=True, slots=True)
class TorrentOrganized(Event):
    """一个种子整理完成：顶层正片都已在最终位置（重命名方式为 none 时即原位置）。

    ``files`` 是正片与字幕的最终路径。投递语义为「至少一次」：未打
    ``ab:renamed`` 标签的种子（如重命名方式为 none）每次进程重启后会再发布一次，
    订阅者须保证幂等。
    """

    kind: ClassVar[str] = "torrent.organized"
    torrent_hash: str
    bangumi_id: int | None
    files: tuple[OrganizedFile, ...]
    downloader_id: str = "default"
