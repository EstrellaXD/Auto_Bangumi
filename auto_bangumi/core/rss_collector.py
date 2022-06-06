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

    def collect(self, bangumi_data):
        try:
            req = requests.get(settings.rss_link, "utf-8")
        except Exception as e:
            logger.exception(e)
            logger.error("ERROR with DNS/Connection.")
        rss = BeautifulSoup(req.text, "xml")
        items = rss.find_all("item")
        for item in items:
            name = item.title.string
            # debug 用
            if settings.debug_mode:
                logger.debug(f"Raw {name}")
            episode = self._simple_analyser.analyse(name)
            if episode:
                group, title, season, ep = episode.group, episode.title, episode.season_info, episode.ep_info
                sub, dpi, source = episode.subtitle, episode.dpi, episode.source
                for d in bangumi_data["bangumi_info"]:
                    if d["title"] == title:
                        break
                else:
                    if ep.number > 1 and settings.enable_eps_complete:
                        download_past = True
                    else:
                        download_past = False
                    bangumi_data["bangumi_info"].append(
                        {
                            "title": title,
                            "season": season.raw,
                            "group": group,
                            "subtitle": sub,
                            "source": source,
                            "dpi": dpi,
                            "added": False,
                            "download_past": download_past
                        }
                    )
                    logger.info(f"Adding {title} Season {season.number}")
