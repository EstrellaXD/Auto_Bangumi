"""Download-client protocol and capability declarations.

`DownloadClient` (the facade) delegates every concrete operation to an object
that implements `DownloaderClient`. Different backends support different subsets
of the qBittorrent surface, so each concrete client advertises what it can do
via a `DownloaderCapabilities` class attribute; the facade consults it and skips
unsupported operations instead of blowing up on a missing method.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, runtime_checkable


@dataclass(frozen=True)
class DownloaderCapabilities:
    """What a concrete download client can do.

    can_query     -- torrents_info / torrents_files / get_torrents_by_tag
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
    ) -> bool: ...


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

    async def check_connection(self) -> str: ...

    # Preferences / setup
    async def prefs_init(self, prefs: dict) -> Any: ...

    async def get_app_prefs(self) -> dict: ...

    async def add_category(self, category: str) -> None: ...

    # Torrent lifecycle
    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ) -> bool: ...

    async def torrents_info(self, status_filter, category, tag=None) -> list[dict]: ...

    async def torrents_files(self, torrent_hash: str) -> list[dict]: ...

    async def torrents_delete(self, hash, delete_files: bool = True) -> bool: ...

    async def torrents_pause(self, hashes: str) -> None: ...

    async def torrents_resume(self, hashes: str) -> None: ...

    async def torrents_rename_file(
        self, torrent_hash, old_path, new_path, verify: bool = True
    ) -> bool: ...

    async def move_torrent(self, hashes, new_location) -> None: ...

    async def set_category(self, _hash, category) -> None: ...

    # Tagging
    async def add_tag(self, _hash, tag) -> None: ...

    # RSS auto-download rules
    async def rss_set_rule(self, rule_name, rule_def) -> None: ...
