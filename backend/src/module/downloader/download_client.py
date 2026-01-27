import asyncio
import logging

from module.conf import settings
from module.models import Bangumi, Torrent
from module.network import RequestContent

from .path import TorrentPath

logger = logging.getLogger(__name__)


class DownloadClient(TorrentPath):
    def __init__(self):
        super().__init__()
        self.client = self.__getClient()
        self.authed = False

    @staticmethod
    def __getClient():
        type = settings.downloader.type
        host = settings.downloader.host
        username = settings.downloader.username
        password = settings.downloader.password
        ssl = settings.downloader.ssl
        if type == "qbittorrent":
            from .client.qb_downloader import QbDownloader

            return QbDownloader(host, username, password, ssl)
        elif type == "aria2":
            from .client.aria2_downloader import Aria2Downloader

            return Aria2Downloader(host, username, password)
        elif type == "mock":
            from .client.mock_downloader import MockDownloader

            logger.info("[Downloader] Using MockDownloader for local development")
            return MockDownloader()
        else:
            logger.error(f"[Downloader] Unsupported downloader type: {type}")
            raise Exception(f"Unsupported downloader type: {type}")

    async def __aenter__(self):
        if not self.authed:
            await self.auth()
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
        return await self.client.check_host()

    async def init_downloader(self):
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
                f"[Downloader] Could not add category (may already exist): {e}"
            )
        if settings.downloader.path == "":
            prefs = await self.client.get_app_prefs()
            settings.downloader.path = self._join_path(prefs["save_path"], "Bangumi")

    async def set_rule(self, data: Bangumi):
        data.rule_name = self._rule_name(data)
        data.save_path = self._gen_save_path(data)
        rule = {
            "enable": True,
            "mustContain": data.title_raw,
            "mustNotContain": "|".join(data.filter),
            "useRegex": True,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": data.rss_link,
            "ignoreDays": 0,
            "lastMatch": "",
            "addPaused": False,
            "assignedCategory": "Bangumi",
            "savePath": data.save_path,
        }
        await self.client.rss_set_rule(rule_name=data.rule_name, rule_def=rule)
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
        return await self.client.torrents_info(
            status_filter=status_filter, category=category, tag=tag
        )

    async def get_torrent_files(self, torrent_hash: str):
        return await self.client.torrents_files(torrent_hash=torrent_hash)

    async def rename_torrent_file(self, _hash, old_path, new_path) -> bool:
        result = await self.client.torrents_rename_file(
            torrent_hash=_hash, old_path=old_path, new_path=new_path
        )
        if result:
            logger.info(f"{old_path} >> {new_path}")
        else:
            logger.debug(f"[Downloader] Rename failed: {old_path} >> {new_path}")
        return result

    async def delete_torrent(self, hashes, delete_files: bool = True):
        await self.client.torrents_delete(hashes, delete_files=delete_files)
        logger.info("[Downloader] Remove torrents.")

    async def pause_torrent(self, hashes: str):
        await self.client.torrents_pause(hashes)

    async def resume_torrent(self, hashes: str):
        await self.client.torrents_resume(hashes)

    async def add_torrent(self, torrent: Torrent | list, bangumi: Bangumi) -> bool:
        if not bangumi.save_path:
            bangumi.save_path = self._gen_save_path(bangumi)
        async with RequestContent() as req:
            if isinstance(torrent, list):
                if len(torrent) == 0:
                    logger.debug(
                        f"[Downloader] No torrent found: {bangumi.official_title}"
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
                logger.debug(f"[Downloader] Add torrent: {bangumi.official_title}")
                return True
            else:
                logger.debug(
                    f"[Downloader] Torrent added before: {bangumi.official_title}"
                )
                return False
        except Exception as e:
            logger.error(
                f"[Downloader] Failed to add torrent for {bangumi.official_title}: {e}"
            )
            return False

    async def move_torrent(self, hashes, location):
        await self.client.move_torrent(hashes=hashes, new_location=location)

    # RSS Parts
    async def add_rss_feed(self, rss_link, item_path="Mikan_RSS"):
        await self.client.rss_add_feed(url=rss_link, item_path=item_path)

    async def remove_rss_feed(self, item_path):
        await self.client.rss_remove_item(item_path=item_path)

    async def get_rss_feed(self):
        return await self.client.rss_get_feeds()

    async def get_download_rules(self):
        return await self.client.get_download_rule()

    async def get_torrent_path(self, hashes):
        return await self.client.get_torrent_path(hashes)

    async def set_category(self, hashes, category):
        await self.client.set_category(hashes, category)

    async def remove_rule(self, rule_name):
        await self.client.remove_rule(rule_name)
        logger.info(f"[Downloader] Delete rule: {rule_name}")

    async def get_torrents_by_tag(self, tag: str) -> list[dict]:
        """Get all torrents with a specific tag."""
        if hasattr(self.client, "get_torrents_by_tag"):
            return await self.client.get_torrents_by_tag(tag)
        return []
