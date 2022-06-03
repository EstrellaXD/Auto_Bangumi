# -*- coding: UTF-8 -*-
import os
import logging
import requests
from bs4 import BeautifulSoup

from conf import settings
from bangumi_parser.analyser.simple_analyser import SimpleAnalyser

logger = logging.getLogger(__name__)


class RSSCollector:
    def __init__(self):
        self._simple_analyser = SimpleAnalyser()

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
            if settings.get_rule_debug:
                logger.debug(f"Raw {name}")
            episoda = self._simple_analyser.analyse(name)
            if episoda:
                title, group, season = episoda.title, episoda.group, episoda.season_info.raw
                for d in bangumi_data["bangumi_info"]:
                    if d["title"] == title:
                        break
                else:
                    bangumi_data["bangumi_info"].append(
                        {
                            "title": title,
                            "season": season,
                            "group": group,
                            "added": False,
                        }
                    )
                    logger.debug(f"add {title} {season}")
