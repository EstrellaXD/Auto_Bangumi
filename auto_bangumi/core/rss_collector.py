# -*- coding: UTF-8 -*-
import os
import logging
import requests
from bs4 import BeautifulSoup

from conf import settings
from bangumi_parser.analyser.rss_parser import ParserLV2

logger = logging.getLogger(__name__)


class RSSCollector:
    def __init__(self):
        self._simple_analyser = ParserLV2()

    def get_rss_info(self, rss_link):
        try:
            req = requests.get(rss_link, "utf-8")
            rss = BeautifulSoup(req.text, "xml")
            return rss
        except Exception as e:
            logger.exception(e)
            logger.error("ERROR with DNS/Connection.")

    def collect(self, bangumi_data):
        rss = self.get_rss_info(settings.rss_link)
        items = rss.find_all("item")
        for item in items:
            name = item.title.string
            # debug 用
            if settings.debug_mode:
                logger.debug(f"Raw {name}")
            episode, data = self.title_parser(name)
            for d in bangumi_data["bangumi_info"]:
                if d["title"] == episode.title:
                    break
                bangumi_data["bangumi_info"].append(data)
                logger.info(f"Adding {episode.title} Season {episode.season_info.number}")

    def title_parser(self, title):
        episode = self._simple_analyser.analyse(title)
        if episode:
            group, title, season, ep = episode.group, episode.title, episode.season_info, episode.ep_info
            sub, dpi, source = episode.subtitle, episode.dpi, episode.source
            if ep.number > 1 and settings.enable_eps_complete:
                download_past = True
            else:
                download_past = False
            data = {
                            "title": title,
                            "season": season.raw,
                            "group": group,
                            "subtitle": sub,
                            "source": source,
                            "dpi": dpi,
                            "added": False,
                            "download_past": download_past
                        }
            return episode, data

    def collect_collection(self, rss_link):
        rss = self.get_rss_info(rss_link)
        item = rss.find("item")
        title = item.title.string
        _, data = self.title_parser(title)
        return data


if __name__ == "__main__":
    rss = RSSCollector()
    data = rss.collect_collection("https://mikanani.me/RSS/Classic")
    print(data)