import re
import logging
import os

from downloader import getClient
from downloader.exceptions import ConflictError

from conf import settings

logger = logging.getLogger(__name__)


class DownloadClient:
    def __init__(self):
        self.client = getClient()

    def init_downloader(self):
        prefs = {
            "rss_auto_downloading_enabled": True,
            "rss_max_articles_per_feed": 500,
            "rss_processing_enabled": True,
            "rss_refresh_interval": 30,
        }
        self.client.prefs_init(prefs=prefs)
        if settings.download_path == "":
            prefs = self.client.get_app_prefs()
            settings.download_path = os.path.join(prefs["save_path"], "Bangumi")

    def set_rule(self, info: dict, rss_link):
        official_name, raw_name, season, group = info["official_title"], info["title_raw"], info["season"], info["group"]
        rule = {
            "enable": True,
            "mustContain": raw_name,
            "mustNotContain": settings.not_contain,
            "useRegex": True,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": [rss_link],
            "ignoreDays": 0,
            "lastMatch": "",
            "addPaused": settings.dev_debug,
            "assignedCategory": "Bangumi",
            "savePath": str(
                os.path.join(
                    settings.download_path,
                    re.sub(settings.rule_name_re, " ", official_name).strip(),
                    f"Season {season}",
                )
            ),
        }
        rule_name = f"[{group}] {official_name}" if settings.enable_group_tag else official_name
        self.client.rss_set_rule(rule_name=f"{rule_name} S{season}", rule_def=rule)
        logger.info(f"Add {official_name} Season {season}")

    def rss_feed(self):
        if not settings.refresh_rss:
            if self.client.get_rss_info() == settings.rss_link:
                logger.info("RSS Already exists.")
            else:
                logger.info("No feed exists, start adding feed.")
                self.client.rss_add_feed(url=settings.rss_link, item_path="Mikan_RSS")
                logger.info("Add RSS Feed successfully.")
        else:
            try:
                self.client.rss_remove_item(item_path="Mikan_RSS")
                logger.info("Remove RSS Feed successfully.")
            except ConflictError:
                logger.info("No feed exists, start adding feed.")
            try:
                self.client.rss_add_feed(url=settings.rss_link, item_path="Mikan_RSS")
                logger.info("Add RSS Feed successfully.")
            except ConnectionError:
                logger.warning("Error with adding RSS Feed.")
            except ConflictError:
                logger.info("RSS Already exists.")

    def add_collection_feed(self, rss_link, item_path):
        self.client.rss_add_feed(url=rss_link, item_path=item_path)
        logger.info("Add RSS Feed successfully.")

    def add_rules(self, bangumi_info, rss_link=settings.rss_link):
        logger.debug("Start adding rules.")
        for info in bangumi_info:
            if not info["added"]:
                self.set_rule(info, rss_link)
                info["added"] = True
        # logger.info("to rule.")
        logger.debug("Finished.")

    def get_torrent_info(self):
        return self.client.torrents_info(
            status_filter="completed", category="Bangumi"
        )

    def rename_torrent_file(self, hash, path_name, new_name):
        self.client.torrents_rename_file(
            torrent_hash=hash, old_path=path_name, new_path=new_name
        )
        logger.info(f"{path_name} >> {new_name}")

    def delete_torrent(self, hashes):
        self.client.torrents_delete(
            hashes
        )
        logger.info(f"Remove bad torrents.")

    def add_torrent(self, torrent: dict):
        self.client.torrents_add(
            urls=torrent["url"],
            save_path=torrent["save_path"],
            category="Bangumi",
            use_auto_torrent_management=True
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


if __name__ == "__main__":
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    put = DownloadClient()
    put.rss_feed()

