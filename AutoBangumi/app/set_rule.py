import re
import logging
import json
import os

from downloader import getClient
from downloader.exceptions import ConflictError

from conf import settings
from utils import json_config

logger = logging.getLogger(__name__)


class SetRule:
    def __init__(self):
        self.info = json_config.load(settings.info_path)
        self.bangumi_info = self.info["bangumi_info"]
        self.rss_link = settings.rss_link
        self.download_path = settings.download_path
        self.client = getClient()

    def set_rule(self, bangumi_name, group, season):
        rule = {
            "enable": True,
            "mustContain": bangumi_name,
            "mustNotContain": settings.not_contain,
            "useRegx": True,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": [self.rss_link],
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
            logger.debug("No feed exists, starting adding feed.")
        try:
            self.client.rss_add_feed(url=self.rss_link, item_path="Mikan_RSS")
            logger.debug("Successes adding RSS Feed.")
        except ConnectionError:
            logger.debug("Error with adding RSS Feed.")
        except ConflictError:
            logger.debug("RSS Already exists.")

    def run(self):
        logger.debug("Start adding rules.")
        for info in self.bangumi_info:
            if not info["added"]:
                self.set_rule(info["title"], info["group"], info["season"])
                info["added"] = True
        json_config.save(settings.info_path, self.info)
        logger.debug("Finished.")


if __name__ == "__main__":
    put = SetRule()
    put.run()
