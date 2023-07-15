import logging
import re

from .path import TorrentPath

from module.models import BangumiData
from module.conf import settings

logger = logging.getLogger(__name__)


class DownloadClient(TorrentPath):
    def __init__(self):
        super().__init__()
        self.client = self.__getClient()
        self.authed = False

    @staticmethod
    def __getClient():
        # TODO 多下载器支持
        type = settings.downloader.type
        host = settings.downloader.host
        username = settings.downloader.username
        password = settings.downloader.password
        ssl = settings.downloader.ssl
        if type == "qbittorrent":
            from .client.qb_downloader import QbDownloader

            return QbDownloader(host, username, password, ssl)
        else:
            logger.error(f"[Downloader] Unsupported downloader type: {type}")
            raise Exception(f"Unsupported downloader type: {type}")

    def __enter__(self):
        if not self.authed:
            self.auth()
        else:
            logger.error("[Downloader] Already authed.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.authed:
            self.client.logout()
            self.authed = False

    def auth(self):
        self.authed = self.client.auth()
        if self.authed:
            logger.debug("[Downloader] Authed.")
        else:
            logger.error("[Downloader] Auth failed.")

    def check_host(self):
        return self.client.check_host()

    def init_downloader(self):
        prefs = {
            "rss_auto_downloading_enabled": True,
            "rss_max_articles_per_feed": 5000,
            "rss_processing_enabled": True,
        }
        self.client.prefs_init(prefs=prefs)
        try:
            self.client.add_category("BangumiCollection")
        except Exception as e:
            logger.debug("[Downloader] Cannot add new category, maybe already exists.")
        if settings.downloader.path == "":
            prefs = self.client.get_app_prefs()
            settings.downloader.path = self._join_path(prefs["save_path"], "Bangumi")

    def set_rule(self, data: BangumiData):
        data.rule_name = self._rule_name(data)
        data.save_path = self._gen_save_path(data)
        raw_title = re.escape(data.title_raw)
        rule = {
            "enable": True,
            "mustContain": raw_title,
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
        self.client.rss_set_rule(rule_name=data.rule_name, rule_def=rule)
        data.added = True
        logger.info(
            f"[Downloader] Add {data.official_title} Season {data.season} to auto download rules."
        )

    def set_rules(self, bangumi_info: list[BangumiData]):
        logger.debug("[Downloader] Start adding rules.")
        for info in bangumi_info:
            self.set_rule(info)
        logger.debug("[Downloader] Finished.")

    def get_torrent_info(self, category="Bangumi", status_filter="completed", tag=None):
        return self.client.torrents_info(
            status_filter=status_filter, category=category, tag=tag
        )

    def rename_torrent_file(self, _hash, old_path, new_path) -> bool:
        logger.info(f"{old_path} >> {new_path}")
        return self.client.torrents_rename_file(
            torrent_hash=_hash, old_path=old_path, new_path=new_path
        )

    def delete_torrent(self, hashes):
        self.client.torrents_delete(hashes)
        logger.info(f"[Downloader] Remove torrents.")

    def add_torrent(self, torrent: dict):
        if self.client.torrents_add(
            urls=torrent.get("urls"),
            torrent_files=torrent.get("torrent_files"),
            save_path=torrent.get("save_path"),
            category="Bangumi",
        ):
            logger.debug(f"[Downloader] Add torrent: {torrent.get('save_path')}")
            return True
        else:
            logger.error(f"[Downloader] Add torrent failed: {torrent.get('save_path')}")
            return False

    def move_torrent(self, hashes, location):
        self.client.move_torrent(hashes=hashes, new_location=location)

    # RSS Parts
    def add_rss_feed(self, rss_link, item_path="Mikan_RSS"):
        self.client.rss_add_feed(url=rss_link, item_path=item_path)

    def remove_rss_feed(self, item_path):
        self.client.rss_remove_item(item_path=item_path)

    def get_rss_feed(self):
        return self.client.rss_get_feeds()

    def get_download_rules(self):
        return self.client.get_download_rule()

    def get_torrent_path(self, hashes):
        return self.client.get_torrent_path(hashes)

    def set_category(self, hashes, category):
        self.client.set_category(hashes, category)

    def remove_rule(self, rule_name):
        self.client.remove_rule(rule_name)
        logger.info(f"[Downloader] Delete rule: {rule_name}")
