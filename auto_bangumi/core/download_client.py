import re
import logging
import os
import time

from downloader import getClient
from downloader.exceptions import ConflictError

from conf import settings

from core.eps_complete import FullSeasonGet


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

    def set_rule(self, info: dict, rss):
        official_name, raw_name, season, group = info["title"], info["title_raw"], info["season"], info["group"]
        rule = {
            "enable": True,
            "mustContain": raw_name,
            "mustNotContain": settings.not_contain,
            "useRegex": True,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": [rss],
            "ignoreDays": 0,
            "lastMatch": "",
            "addPaused": settings.dev_debug,
            "assignedCategory": "Bangumi",
            "savePath": str(
                os.path.join(
                    settings.download_path,
                    re.sub(settings.rule_name_re, " ", official_name).strip(),
                    season,
                )
            ),
        }
        rule_name = f"[{group}] {official_name}" if settings.enable_group_tag else official_name
        self.client.rss_set_rule(rule_name=f"{rule_name} {season}", rule_def=rule)

    def rss_feed(self):
        try:
            self.client.rss_remove_item(item_path="Mikan_RSS")
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

    def add_rules(self, bangumi_info, rss_link):
        logger.info("Start adding rules.")
        for info in bangumi_info:
            if not info["added"]:
                self.set_rule(info, rss_link)
                info["added"] = True
        logger.info("Finished.")

    def eps_collect(self, bangumi_info):
        logger.info("Start collecting past episodes.")
        for info in bangumi_info:
            if info["download_past"]:
                downloads = FullSeasonGet(
                    info["group"],
                    info["title"],
                    info["season"],
                    info["subtitle"],
                    info["source"],
                    info["dpi"]
                ).add_torrents_info()
                for download in downloads:
                    self.client.torrents_add(
                        urls=download["url"],
                        save_path=download["save_path"],
                        category="Bangumi"
                    )
                time.sleep(settings.connect_retry_interval)
                info["download_past"] = False

    def get_torrent_info(self):
        return self.client.torrents_info(
            status_filter="completed", category="Bangumi"
        )

    def rename_torrent_file(self, hash, path_name, new_name):
        self.client.torrents_rename_file(
            torrent_hash=hash, old_path=path_name, new_path=new_name
        )
        logger.info(f"{path_name} >> {new_name}")

    def delete_torrent(self, hash):
        self.client.torrents_delete(
            hash
        )
        logger.info(f"Remove bad torrents.")


if __name__ == "__main__":
    put = DownloadClient()

