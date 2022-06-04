import re
import logging
import os

from downloader import getClient
from downloader.exceptions import ConflictError

from conf import settings
from utils import json_config

from core.eps_complete import FullSeasonGet


logger = logging.getLogger(__name__)


class DownloadClient:
    def __init__(self):
        self.client = getClient()

    def set_rule(self, bangumi_name, group, season):
        rule = {
            "enable": True,
            "mustContain": bangumi_name,
            "mustNotContain": settings.not_contain,
            "useRegex": True,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": [settings.rss_link],
            "ignoreDays": 0,
            "lastMatch": "",
            "addPaused": False,
            "assignedCategory": "Bangumi",
            "savePath": str(
                os.path.join(
                    settings.download_path,
                    re.sub(settings.rule_name_re, " ", bangumi_name).strip(),
                    season,
                )
            ),
        }
        if settings.enable_group_tag:
            rule_name = f"[{group}] {bangumi_name}"
        else:
            rule_name = bangumi_name
        self.client.rss_set_rule(rule_name=rule_name, rule_def=rule)

    def rss_feed(self):
        try:
            self.client.rss_remove_item(item_path="Mikan_RSS")
        except ConflictError:
            logger.info("No feed exists, starting adding feed.")
        try:
            self.client.rss_add_feed(url=settings.rss_link, item_path="Mikan_RSS")
            logger.info("Successes adding RSS Feed.")
        except ConnectionError:
            logger.warning("Error with adding RSS Feed.")
        except ConflictError:
            logger.info("RSS Already exists.")

    def add_rules(self, bangumi_info):
        logger.info("Start adding rules.")
        for info in bangumi_info:
            if not info["added"]:
                self.set_rule(info["title"], info["group"], info["season"])
                info["added"] = True
        logger.info("Finished.")

    def eps_collect(self, bangumi_info):
        logger.info("Start collect past eps.")
        for info in bangumi_info:
            if info["download_past"]:
                FullSeasonGet(info["group"], info["title"], info["season"]).run()
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


if __name__ == "__main__":
    put = DownloadClient()
    put.add_rules()
