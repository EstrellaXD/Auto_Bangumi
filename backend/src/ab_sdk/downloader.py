"""下载器契约：宿主的下载门面（DownloadClient）通过它驱动具体下载器。

第三方下载器插件用 ``@provider(points.DOWNLOADER, id="...")`` 返回一个
:data:`DownloaderFactory`：接收连接参数，返回实现 :class:`DownloaderClient`
（至少 :class:`CoreDownloaderClient`）的对象。不同下载器能力不同，通过
``capabilities`` 类属性声明，门面会跳过不支持的操作而不是报错。
用户在设置里把下载器实例的 ``provider`` 设为该 id 即可启用。
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Protocol, runtime_checkable


class AddResult(Enum):
    """Torrent-add result shared by concrete clients and the facade."""

    ADDED = "added"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class RenameOutcome(str, Enum):
    """Downloader-independent outcome of a single file rename."""

    RENAMED = "renamed"
    ALREADY_APPLIED = "already_applied"
    DESTINATION_EXISTS = "destination_exists"
    RETRYABLE_FAILURE = "retryable_failure"


@dataclass(frozen=True)
class RenameResult:
    """Structured rename result preserved across the downloader facade.

    ``bool(result)`` deliberately keeps the old success/failure behaviour while
    callers migrate to inspecting :attr:`outcome`.  It must never make a
    collision or retryable failure truthy.
    """

    outcome: RenameOutcome
    detail: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome in {
            RenameOutcome.RENAMED,
            RenameOutcome.ALREADY_APPLIED,
        }

    def __bool__(self) -> bool:
        return self.succeeded


@dataclass(frozen=True)
class DownloaderCapabilities:
    """What a concrete download client can do.

    can_query     -- torrents_info / torrents_files
    can_rename    -- torrents_rename_file
    can_manage    -- delete / pause / resume / move / category / tags
    can_rss_rules -- qB-native RSS feeds + auto-download rules + prefs
    """

    can_query: bool
    can_rename: bool
    can_manage: bool
    can_rss_rules: bool


@runtime_checkable
class CoreDownloaderClient(Protocol):
    """The minimum every backend must implement: authenticate and add torrents."""

    capabilities: ClassVar[DownloaderCapabilities]

    async def auth(self, retry: int = 3) -> bool: ...

    async def logout(self) -> None: ...

    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ) -> AddResult: ...


@runtime_checkable
class DownloaderClient(Protocol):
    """The full async surface `DownloadClient` delegates to.

    A backend that satisfies this protocol supports every facade operation. A
    backend that only satisfies `CoreDownloaderClient` is limited to auth and
    adding torrents; the facade guards the rest with `capabilities`.
    """

    capabilities: ClassVar[DownloaderCapabilities]

    # Session lifecycle / connectivity
    async def auth(self, retry: int = 3) -> bool: ...

    async def logout(self) -> None: ...

    # Preferences / setup

    async def add_category(self, category: str) -> None: ...

    # Torrent lifecycle
    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ) -> AddResult: ...

    async def torrents_info(self, status_filter, category, tag=None) -> list[dict]: ...

    async def torrent_exists(self, torrent_hash: str) -> bool | None: ...

    async def torrents_files(self, torrent_hash: str) -> list[dict]: ...

    async def torrents_delete(self, hash, delete_files: bool = True) -> bool: ...

    async def torrents_pause(self, hashes: str) -> None: ...

    async def torrents_resume(self, hashes: str) -> None: ...

    async def torrents_rename_file(
        self, torrent_hash, old_path, new_path, verify: bool = True
    ) -> RenameResult: ...

    async def move_torrent(self, hashes, new_location) -> None: ...

    async def set_category(self, _hash, category) -> None: ...

    # Tagging
    async def add_tag(self, _hash, tag) -> None: ...

    # RSS auto-download rules
    async def rss_set_rule(self, rule_name, rule_def) -> None: ...


@dataclass(frozen=True)
class DownloaderConnection:
    """来自设置页「下载器」一节的连接参数。"""

    host: str
    username: str
    password: str
    ssl: bool
    # 实例 id（``plugins.instances[].id``），供需要按实例保存本地状态的下载器使用
    instance_id: str = "default"


DownloaderFactory = Callable[[DownloaderConnection], CoreDownloaderClient]
