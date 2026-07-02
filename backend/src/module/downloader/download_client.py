import asyncio
import logging

from module.conf import settings
from module.models import Bangumi, Torrent
from module.network import RequestContent

from .path import gen_save_path, join_path, rule_name
from .rules import build_rss_rule

logger = logging.getLogger(__name__)

# Warn at most once per (client type, operation) when a backend cannot perform
# an operation, so aria2 users are not spammed every rename cycle.
_warned_unsupported: set[tuple[str, str]] = set()


class DownloadClient:
    """Unified async download client.

    Wraps qBittorrent, Aria2, or MockDownloader behind a common interface.
    Intended to be used as an async context manager; authentication is
    performed on ``__aenter__`` and the session is closed on ``__aexit__``.
    """

    def __init__(self):
        self.client = self.__getClient()
        self.authed = False

    @staticmethod
    def __getClient():
        """Instantiate the configured downloader client (qbittorrent | aria2 | mock)."""
        downloader_type = settings.downloader.type
        host = settings.downloader.host
        username = settings.downloader.username
        password = settings.downloader.password
        ssl = settings.downloader.ssl
        if downloader_type == "qbittorrent":
            from .client.qb_downloader import QbDownloader

            return QbDownloader(host, username, password, ssl)
        elif downloader_type == "aria2":
            from .client.aria2_downloader import Aria2Downloader

            return Aria2Downloader(host, username, password)
        elif downloader_type == "mock":
            from .client.mock_downloader import MockDownloader

            logger.debug("[Downloader] Using MockDownloader for local development")
            return MockDownloader()
        else:
            logger.error(
                "[Downloader] Unsupported downloader type: %s", downloader_type
            )
            raise Exception(f"Unsupported downloader type: {downloader_type}")

    def _supports(self, capability: str, op: str) -> bool:
        """Whether the concrete client can perform ``op`` (log once if not)."""
        caps = getattr(self.client, "capabilities", None)
        if caps is not None and getattr(caps, capability, False):
            return True
        key = (type(self.client).__name__, op)
        if key not in _warned_unsupported:
            _warned_unsupported.add(key)
            logger.warning(
                "[Downloader] %s does not support '%s'; skipping.",
                type(self.client).__name__,
                op,
            )
        return False

    async def __aenter__(self):
        if not self.authed:
            await self.auth()
            if not self.authed:
                # __aexit__ never runs when we raise here, so close the
                # concrete client's connection pool now or it leaks on every
                # failed connect (#1043).
                await self.client.logout()
                raise ConnectionError("Download client authentication failed")
        else:
            logger.error("[Downloader] Already authed.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.authed:
            await self.client.logout()
            self.authed = False

    async def auth(self):
        self.authed = await self.client.auth()
        if self.authed:
            logger.debug("[Downloader] Authed.")
        else:
            logger.error("[Downloader] Auth failed.")

    async def check_host(self):
        if not self._supports("can_query", "check_host"):
            return False
        return await self.client.check_host()

    async def init_downloader(self):
        """Apply required qBittorrent RSS preferences and create the Bangumi category."""
        if not self._supports("can_rss_rules", "init_downloader"):
            return
        prefs = {
            "rss_auto_downloading_enabled": True,
            "rss_max_articles_per_feed": 500,
            "rss_processing_enabled": True,
            "rss_refresh_interval": 30,
        }
        await self.client.prefs_init(prefs=prefs)
        # Category creation may fail if it already exists (HTTP 409) or network issues
        try:
            await self.client.add_category("BangumiCollection")
        except Exception as e:
            logger.debug(
                "[Downloader] Could not add category (may already exist): %s", e
            )
        if settings.downloader.path == "":
            prefs = await self.client.get_app_prefs()
            settings.downloader.path = join_path(prefs["save_path"], "Bangumi")

    async def set_rss_rule(self, rule_name: str, rule: dict):
        """Create or update a raw qBittorrent RSS auto-download rule."""
        if not self._supports("can_rss_rules", "set_rss_rule"):
            return
        await self.client.rss_set_rule(rule_name=rule_name, rule_def=rule)

    async def set_rule(self, data: Bangumi):
        """Create or update a qBittorrent RSS auto-download rule for one bangumi entry."""
        data.rule_name = rule_name(data)
        data.save_path = gen_save_path(data)
        rule = build_rss_rule(data, data.save_path)
        await self.set_rss_rule(data.rule_name, rule)
        data.added = True
        logger.info(
            f"[Downloader] Add {data.official_title} Season {data.season} to auto download rules."
        )

    async def set_rules(self, bangumi_info: list[Bangumi]):
        logger.debug("[Downloader] Start adding rules.")
        await asyncio.gather(*[self.set_rule(info) for info in bangumi_info])
        logger.debug("[Downloader] Finished.")

    async def get_torrent_info(
        self, category="Bangumi", status_filter="completed", tag=None
    ):
        if not self._supports("can_query", "get_torrent_info"):
            return []
        return await self.client.torrents_info(
            status_filter=status_filter, category=category, tag=tag
        )

    async def get_torrent_files(self, torrent_hash: str):
        if not self._supports("can_query", "get_torrent_files"):
            return []
        return await self.client.torrents_files(torrent_hash=torrent_hash)

    async def rename_torrent_file(
        self, _hash, old_path, new_path, verify: bool = True
    ) -> bool:
        if not self._supports("can_rename", "rename_torrent_file"):
            return False
        result = await self.client.torrents_rename_file(
            torrent_hash=_hash, old_path=old_path, new_path=new_path, verify=verify
        )
        if result:
            logger.info(f"{old_path} >> {new_path}")
        else:
            logger.debug("[Downloader] Rename failed: %s >> %s", old_path, new_path)
        return result

    async def delete_torrent(self, hashes, delete_files: bool = True) -> bool:
        if not self._supports("can_manage", "delete_torrent"):
            return False
        ok = await self.client.torrents_delete(hashes, delete_files=delete_files)
        if ok:
            logger.info("[Downloader] Remove torrents.")
        else:
            logger.error("[Downloader] Failed to remove torrents.")
        return ok

    async def pause_torrent(self, hashes: str):
        if not self._supports("can_manage", "pause_torrent"):
            return
        await self.client.torrents_pause(hashes)

    async def resume_torrent(self, hashes: str):
        if not self._supports("can_manage", "resume_torrent"):
            return
        await self.client.torrents_resume(hashes)

    async def add_torrent(self, torrent: Torrent | list, bangumi: Bangumi) -> bool:
        """Download a torrent (or list of torrents) for the given bangumi entry.

        Handles both magnet links and .torrent file URLs, fetching file bytes
        when necessary. Tags each torrent with ``ab:<bangumi_id>`` for later
        episode-offset lookup during rename.
        """
        if not bangumi.save_path:
            bangumi.save_path = gen_save_path(bangumi)
        async with RequestContent() as req:
            if isinstance(torrent, list):
                if len(torrent) == 0:
                    logger.debug(
                        "[Downloader] No torrent found: %s", bangumi.official_title
                    )
                    return False
                if "magnet" in torrent[0].url:
                    torrent_url = [t.url for t in torrent]
                    torrent_file = None
                else:
                    torrent_file = await asyncio.gather(
                        *[req.get_content(t.url) for t in torrent]
                    )
                    # Filter out None values (failed fetches)
                    torrent_file = [f for f in torrent_file if f is not None]
                    if not torrent_file:
                        logger.warning(
                            f"[Downloader] Failed to fetch torrent files for: {bangumi.official_title}"
                        )
                        return False
                    torrent_url = None
            else:
                if "magnet" in torrent.url:
                    torrent_url = torrent.url
                    torrent_file = None
                else:
                    torrent_file = await req.get_content(torrent.url)
                    if torrent_file is None:
                        logger.warning(
                            f"[Downloader] Failed to fetch torrent file for: {bangumi.official_title}"
                        )
                        return False
                    torrent_url = None
        # Create tag with bangumi_id for offset lookup during rename
        tags = f"ab:{bangumi.id}" if bangumi.id else None
        try:
            if await self.client.add_torrents(
                torrent_urls=torrent_url,
                torrent_files=torrent_file,
                save_path=bangumi.save_path,
                category="Bangumi",
                tags=tags,
            ):
                logger.debug("[Downloader] Add torrent: %s", bangumi.official_title)
                return True
            else:
                logger.debug(
                    "[Downloader] Torrent added before: %s", bangumi.official_title
                )
                return False
        except Exception as e:
            logger.error(
                f"[Downloader] Failed to add torrent for {bangumi.official_title}: {e}"
            )
            return False

    async def move_torrent(self, hashes, location):
        if not self._supports("can_manage", "move_torrent"):
            return
        await self.client.move_torrent(hashes=hashes, new_location=location)

    # RSS Parts
    async def add_rss_feed(self, rss_link, item_path="Mikan_RSS"):
        if not self._supports("can_rss_rules", "add_rss_feed"):
            return
        await self.client.rss_add_feed(url=rss_link, item_path=item_path)

    async def remove_rss_feed(self, item_path):
        if not self._supports("can_rss_rules", "remove_rss_feed"):
            return
        await self.client.rss_remove_item(item_path=item_path)

    async def get_rss_feed(self):
        if not self._supports("can_rss_rules", "get_rss_feed"):
            return {}
        return await self.client.rss_get_feeds()

    async def get_download_rules(self):
        if not self._supports("can_rss_rules", "get_download_rules"):
            return {}
        return await self.client.get_download_rule()

    async def get_torrent_path(self, hashes):
        if not self._supports("can_query", "get_torrent_path"):
            return ""
        return await self.client.get_torrent_path(hashes)

    async def set_category(self, hashes, category):
        if not self._supports("can_manage", "set_category"):
            return
        await self.client.set_category(hashes, category)

    async def remove_rule(self, rule_name):
        if not self._supports("can_rss_rules", "remove_rule"):
            return
        await self.client.remove_rule(rule_name)
        logger.info(f"[Downloader] Delete rule: {rule_name}")

    async def get_torrents_by_tag(self, tag: str) -> list[dict]:
        """Get all torrents with a specific tag."""
        if not self._supports("can_query", "get_torrents_by_tag"):
            return []
        return await self.client.get_torrents_by_tag(tag)

    async def add_tag(self, torrent_hash: str, tag: str):
        """Add a tag to a torrent."""
        if not self._supports("can_manage", "add_tag"):
            return
        await self.client.add_tag(torrent_hash, tag)
        logger.debug(
            "[Downloader] Added tag '%s' to torrent %s...", tag, torrent_hash[:8]
        )
