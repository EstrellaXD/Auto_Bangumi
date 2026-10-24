"""
Mock Downloader for local development and testing.

This downloader simulates qBittorrent behavior without requiring an actual
qBittorrent instance. All operations return success and log their actions.
"""

import logging
from typing import Any, ClassVar

from module.downloader.base import (
    AddResult,
    DownloaderCapabilities,
    RenameOutcome,
    RenameResult,
)

logger = logging.getLogger(__name__)


class MockDownloader:
    """
    A mock downloader that simulates qBittorrent API responses.
    All methods return success values and log their operations.
    """

    capabilities: ClassVar[DownloaderCapabilities] = DownloaderCapabilities(
        can_query=True,
        can_rename=True,
        can_manage=True,
        can_rss_rules=True,
    )

    def __init__(self):
        self._torrents: dict[str, dict] = {}
        self._rules: dict[str, dict] = {}
        self._categories: set[str] = {"Bangumi", "BangumiCollection"}
        self._authed = False
        logger.debug("Initialized")

    async def auth(self, retry=3) -> bool:
        # No real session; idempotent by construction, kept for parity with
        # QbDownloader so session-reuse tests stay meaningful.
        self._authed = True
        logger.debug("Auth successful (mocked)")
        return True

    async def logout(self):
        self._authed = False
        logger.debug("Logout (mocked)")

    async def add_category(self, category: str):
        self._categories.add(category)
        logger.debug("add_category: %s", category)

    async def torrents_info(
        self, status_filter: str | None, category: str | None, tag: str | None = None
    ) -> list[dict]:
        """Return list of torrents matching the filter."""
        logger.debug(
            "torrents_info(filter=%s, category=%s, tag=%s)",
            status_filter,
            category,
            tag,
        )
        result = []
        for hash_, torrent in self._torrents.items():
            if category and torrent.get("category") != category:
                continue
            if tag and tag not in torrent.get("tags", []):
                continue
            result.append(torrent)
        return result

    async def torrent_exists(self, torrent_hash: str) -> bool | None:
        return torrent_hash in self._torrents

    async def torrents_files(self, torrent_hash: str) -> list[dict]:
        """Return files for a torrent."""
        logger.debug("torrents_files(%s)", torrent_hash)
        torrent = self._torrents.get(torrent_hash, {})
        return torrent.get("files", [])

    async def add_torrents(
        self,
        torrent_urls: str | list | None,
        torrent_files: bytes | list | None,
        save_path: str,
        category: str,
        tags: str | None = None,
    ) -> AddResult:
        """Add a torrent. Returns ADDED for success."""
        import hashlib
        import time

        # Generate a mock hash
        content = str(torrent_urls or torrent_files or time.time())
        mock_hash = hashlib.sha1(content.encode()).hexdigest()

        self._torrents[mock_hash] = {
            "hash": mock_hash,
            "name": f"mock_torrent_{mock_hash[:8]}",
            "save_path": save_path,
            "category": category,
            "state": "downloading",
            "progress": 0.0,
            "files": [],
            "tags": tags or "",
        }
        logger.info(f"add_torrents -> hash={mock_hash[:16]}... save_path={save_path}")
        return AddResult.ADDED

    @staticmethod
    def _normalize_hashes(hashes: str | list | tuple) -> list[str]:
        """Accept a single hash, a pipe-joined string, or a list/tuple of
        hashes and always return a list -- mirrors the real qB client's
        normalization so switching downloader backends doesn't change
        behavior (#1046)."""
        if isinstance(hashes, (list, tuple)):
            return list(hashes)
        return hashes.split("|") if "|" in hashes else [hashes]

    async def torrents_delete(
        self, hash: str | list, delete_files: bool = True
    ) -> bool:
        for h in self._normalize_hashes(hash):
            self._torrents.pop(h, None)
        logger.debug("torrents_delete(%s, delete_files=%s)", hash, delete_files)
        return True

    async def torrents_pause(self, hashes: str | list):
        for h in self._normalize_hashes(hashes):
            if h in self._torrents:
                self._torrents[h]["state"] = "paused"
        logger.debug("torrents_pause(%s)", hashes)

    async def torrents_resume(self, hashes: str | list):
        for h in self._normalize_hashes(hashes):
            if h in self._torrents:
                self._torrents[h]["state"] = "downloading"
        logger.debug("torrents_resume(%s)", hashes)

    async def torrents_rename_file(
        self, torrent_hash: str, old_path: str, new_path: str, verify: bool = True
    ) -> RenameResult:
        logger.info(f"rename: {old_path} -> {new_path}")
        return RenameResult(RenameOutcome.RENAMED)

    async def rss_set_rule(self, rule_name: str, rule_def: dict):
        self._rules[rule_name] = rule_def
        logger.info(f"rss_set_rule({rule_name})")

    async def move_torrent(self, hashes: str | list, new_location: str):
        for h in self._normalize_hashes(hashes):
            if h in self._torrents:
                self._torrents[h]["save_path"] = new_location
        logger.debug("move_torrent(%s, %s)", hashes, new_location)

    async def set_category(self, _hash: str | list, category: str):
        for h in self._normalize_hashes(_hash):
            if h in self._torrents:
                self._torrents[h]["category"] = category
        logger.debug("set_category(%s, %s)", _hash, category)

    async def add_tag(self, _hash: str, tag: str):
        if _hash in self._torrents:
            tags = self._torrents[_hash].setdefault("tags", [])
            if tag not in tags:
                tags.append(tag)
        logger.debug("add_tag(%s, %s)", _hash, tag)

    # Helper methods for testing

    def add_mock_torrent(
        self,
        name: str,
        hash: str | None = None,
        category: str = "Bangumi",
        state: str = "completed",
        save_path: str = "/tmp/mock-downloads",
        files: list[dict] | None = None,
    ) -> str:
        """Add a mock torrent for testing purposes."""
        import hashlib

        if hash is None:
            hash = hashlib.sha1(name.encode()).hexdigest()

        self._torrents[hash] = {
            "hash": hash,
            "name": name,
            "save_path": save_path,
            "category": category,
            "state": state,
            "progress": 1.0 if state == "completed" else 0.5,
            "files": files or [{"name": f"{name}.mkv", "size": 1024 * 1024 * 500}],
            "tags": [],
        }
        logger.debug("Added mock torrent: %s", name)
        return hash

    def get_state(self) -> dict[str, Any]:
        """Get the current mock state for debugging."""
        return {
            "torrents": self._torrents,
            "rules": self._rules,
            "categories": list(self._categories),
        }
