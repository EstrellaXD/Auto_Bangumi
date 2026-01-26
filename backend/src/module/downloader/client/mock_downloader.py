"""
Mock Downloader for local development and testing.

This downloader simulates qBittorrent behavior without requiring an actual
qBittorrent instance. All operations return success and log their actions.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MockDownloader:
    """
    A mock downloader that simulates qBittorrent API responses.
    All methods return success values and log their operations.
    """

    def __init__(self):
        self._torrents: dict[str, dict] = {}
        self._rules: dict[str, dict] = {}
        self._feeds: dict[str, dict] = {}
        self._categories: set[str] = {"Bangumi", "BangumiCollection"}
        self._prefs = {
            "save_path": "/tmp/mock-downloads",
            "rss_auto_downloading_enabled": True,
            "rss_max_articles_per_feed": 500,
            "rss_processing_enabled": True,
            "rss_refresh_interval": 30,
        }
        logger.info("[MockDownloader] Initialized")

    async def auth(self, retry=3) -> bool:
        logger.info("[MockDownloader] Auth successful (mocked)")
        return True

    async def logout(self):
        logger.debug("[MockDownloader] Logout (mocked)")

    async def check_host(self) -> bool:
        logger.debug("[MockDownloader] check_host -> True")
        return True

    async def prefs_init(self, prefs: dict):
        self._prefs.update(prefs)
        logger.debug(f"[MockDownloader] prefs_init: {prefs}")

    async def get_app_prefs(self) -> dict:
        logger.debug("[MockDownloader] get_app_prefs")
        return self._prefs

    async def add_category(self, category: str):
        self._categories.add(category)
        logger.debug(f"[MockDownloader] add_category: {category}")

    async def torrents_info(
        self, status_filter: str | None, category: str | None, tag: str | None = None
    ) -> list[dict]:
        """Return list of torrents matching the filter."""
        logger.debug(
            f"[MockDownloader] torrents_info(filter={status_filter}, category={category}, tag={tag})"
        )
        result = []
        for hash_, torrent in self._torrents.items():
            if category and torrent.get("category") != category:
                continue
            if tag and tag not in torrent.get("tags", []):
                continue
            result.append(torrent)
        return result

    async def torrents_files(self, torrent_hash: str) -> list[dict]:
        """Return files for a torrent."""
        logger.debug(f"[MockDownloader] torrents_files({torrent_hash})")
        torrent = self._torrents.get(torrent_hash, {})
        return torrent.get("files", [])

    async def add_torrents(
        self,
        torrent_urls: str | list | None,
        torrent_files: bytes | list | None,
        save_path: str,
        category: str,
        tags: str | None = None,
    ) -> bool:
        """Add a torrent. Returns True for success."""
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
        logger.info(
            f"[MockDownloader] add_torrents -> hash={mock_hash[:16]}... save_path={save_path}"
        )
        return True

    async def torrents_delete(self, hash: str, delete_files: bool = True):
        hashes = hash.split("|") if "|" in hash else [hash]
        for h in hashes:
            self._torrents.pop(h, None)
        logger.debug(f"[MockDownloader] torrents_delete({hash}, delete_files={delete_files})")

    async def torrents_pause(self, hashes: str):
        for h in hashes.split("|"):
            if h in self._torrents:
                self._torrents[h]["state"] = "paused"
        logger.debug(f"[MockDownloader] torrents_pause({hashes})")

    async def torrents_resume(self, hashes: str):
        for h in hashes.split("|"):
            if h in self._torrents:
                self._torrents[h]["state"] = "downloading"
        logger.debug(f"[MockDownloader] torrents_resume({hashes})")

    async def torrents_rename_file(
        self, torrent_hash: str, old_path: str, new_path: str
    ) -> bool:
        logger.info(f"[MockDownloader] rename: {old_path} -> {new_path}")
        return True

    async def rss_add_feed(self, url: str, item_path: str):
        self._feeds[item_path] = {"url": url, "path": item_path}
        logger.debug(f"[MockDownloader] rss_add_feed({url}, {item_path})")

    async def rss_remove_item(self, item_path: str):
        self._feeds.pop(item_path, None)
        logger.debug(f"[MockDownloader] rss_remove_item({item_path})")

    async def rss_get_feeds(self) -> dict:
        logger.debug("[MockDownloader] rss_get_feeds")
        return self._feeds

    async def rss_set_rule(self, rule_name: str, rule_def: dict):
        self._rules[rule_name] = rule_def
        logger.info(f"[MockDownloader] rss_set_rule({rule_name})")

    async def move_torrent(self, hashes: str, new_location: str):
        for h in hashes.split("|"):
            if h in self._torrents:
                self._torrents[h]["save_path"] = new_location
        logger.debug(f"[MockDownloader] move_torrent({hashes}, {new_location})")

    async def get_download_rule(self) -> dict:
        logger.debug("[MockDownloader] get_download_rule")
        return self._rules

    async def get_torrent_path(self, _hash: str) -> str:
        torrent = self._torrents.get(_hash, {})
        path = torrent.get("save_path", "/tmp/mock-downloads")
        logger.debug(f"[MockDownloader] get_torrent_path({_hash}) -> {path}")
        return path

    async def set_category(self, _hash: str, category: str):
        if _hash in self._torrents:
            self._torrents[_hash]["category"] = category
        logger.debug(f"[MockDownloader] set_category({_hash}, {category})")

    async def remove_rule(self, rule_name: str):
        self._rules.pop(rule_name, None)
        logger.debug(f"[MockDownloader] remove_rule({rule_name})")

    async def add_tag(self, _hash: str, tag: str):
        if _hash in self._torrents:
            tags = self._torrents[_hash].setdefault("tags", [])
            if tag not in tags:
                tags.append(tag)
        logger.debug(f"[MockDownloader] add_tag({_hash}, {tag})")

    async def check_connection(self) -> str:
        return "v4.6.0 (mock)"

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
        logger.debug(f"[MockDownloader] Added mock torrent: {name}")
        return hash

    def get_state(self) -> dict[str, Any]:
        """Get the current mock state for debugging."""
        return {
            "torrents": self._torrents,
            "rules": self._rules,
            "feeds": self._feeds,
            "categories": list(self._categories),
        }
