import re
import logging
import os

from module.downloader import getClient
from module.conf import settings
from module.models import BangumiData


logger = logging.getLogger(__name__)


class DownloadClient:
    def __init__(self):
        self.client = getClient()
        self.authed = False

    def auth(self):
        host, username, password = settings.downloader.host, settings.downloader.username, settings.downloader.password
        try:
            self.client.auth(host, username, password)
            self.authed = True
        except Exception as e:
            logger.error(f"Can't login {host} by {username}, {e}")

    def init_downloader(self):
        prefs = {
            "rss_auto_downloading_enabled": True,
            "rss_max_articles_per_feed": 500,
            "rss_processing_enabled": True,
            "rss_refresh_interval": 30,
        }
        self.client.prefs_init(prefs=prefs)
        if settings.downloader.path == "":
            prefs = self.client.get_app_prefs()
            settings.downloader.path = os.path.join(prefs["save_path"], "Bangumi")

    def set_rule(self, info: BangumiData, rss_link):
        official_name, raw_name, season, group = info.official_title, info.title_raw, info.season, info.group
        rule = {
            "enable": True,
            "mustContain": raw_name,
            "mustNotContain": "|".join(settings.rss_parser.filter),
            "useRegex": True,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": [rss_link],
            "ignoreDays": 0,
            "lastMatch": "",
            "addPaused": False,
            "assignedCategory": "Bangumi",
            "savePath": str(
                os.path.join(
                    settings.downloader.path,
                    re.sub(r"[:/.]", " ", official_name).strip(),
                    f"Season {season}",
                )
            ),
        }
        rule_name = f"[{group}] {official_name}" if settings.bangumi_manage.group_tag else official_name
        self.client.rss_set_rule(rule_name=f"{rule_name} S{season}", rule_def=rule)
        logger.info(f"Add {official_name} Season {season}")

    def rss_feed(self, rss_link):
        # TODO: 定时刷新 RSS
        if self.client.get_rss_info() == rss_link:
            logger.info("RSS Already exists.")
        else:
            logger.info("No feed exists, start adding feed.")
            self.client.rss_add_feed(url=rss_link, item_path="Mikan_RSS")
            logger.info("Add RSS Feed successfully.")

    def add_collection_feed(self, rss_link, item_path):
        self.client.rss_add_feed(url=rss_link, item_path=item_path)
        logger.info("Add RSS Feed successfully.")

    def add_rules(self, bangumi_info: list[BangumiData], rss_link: str):
        logger.debug("Start adding rules.")
        for info in bangumi_info:
            if not info.added:
                self.set_rule(info, rss_link)
                info.added = True
        logger.debug("Finished.")

    def get_torrent_info(self, category="Bangumi"):
        return self.client.torrents_info(
            status_filter="completed", category=category
        )

    def rename_torrent_file(self, _hash, old_path, new_path):
        self.client.torrents_rename_file(
            torrent_hash=_hash, old_path=old_path, new_path=new_path
        )
        logger.info(f"{old_path} >> {new_path}")

    def delete_torrent(self, hashes):
        self.client.torrents_delete(
            hashes
        )
        logger.info(f"Remove bad torrents.")

    def add_torrent(self, torrent: dict):
        self.client.torrents_add(
            urls=torrent["url"],
            save_path=torrent["save_path"],
            category="Bangumi"
        )

    def move_torrent(self, hashes, location):
        self.client.move_torrent(
            hashes=hashes,
            new_location=location
        )

    def add_rss_feed(self, rss_link, item_path):
        self.client.rss_add_feed(url=rss_link, item_path=item_path)
        logger.info("Add RSS Feed successfully.")

    def get_download_rules(self):
        return self.client.get_download_rule()

    def get_torrent_path(self, hashes):
        return self.client.get_torrent_path(hashes)

    def set_category(self, hashes, category):
        self.client.set_category(hashes, category)

