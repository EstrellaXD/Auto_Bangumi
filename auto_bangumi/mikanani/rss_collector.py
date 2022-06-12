# -*- coding: UTF-8 -*-
import logging

from conf import settings
from bangumi_parser.analyser.rss_parser import ParserLV2
from bangumi_parser.fuzz_match import FuzzMatch
from network.request import RequestsURL

logger = logging.getLogger(__name__)


class RSSCollector:
    def __init__(self, request: RequestsURL):
        self._simple_analyser = ParserLV2()
        self._fuzz_match = FuzzMatch()
        self._req = request

    def title_parser(self, title, fuzz_match=True):
        episode = self._simple_analyser.analyse(title)
        if episode:
            group, title_raw, season, ep = episode.group, episode.title, episode.season_info, episode.ep_info
            sub, dpi, source = episode.subtitle, episode.dpi, episode.source
            if ep.number > 1 and settings.enable_eps_complete:
                download_past = True
            else:
                download_past = False
            if fuzz_match:
                match_value, title_official = self._fuzz_match.find_max_name(title_raw)
            else:
                match_value, title_official = 0, None
            title_official = title_official if match_value > 55 else title_raw
            data = {
                "title": title_official,
                "title_raw": title_raw,
                "season": season.raw,
                "group": group,
                "subtitle": sub,
                "source": source,
                "dpi": dpi,
                "added": False,
                "download_past": download_past
            }
            return episode, data, title_official

    def collect(self, bangumi_data):
        req = self._req.get_url(settings.rss_link)
        items = req.find_all("item")
        for item in items:
            add = True
            name = item.title.string
            episode, data, title_official = self.title_parser(name)
            for d in bangumi_data["bangumi_info"]:
                if d["title"] == title_official:
                    add = False
                    break
            if add:
                if settings.debug_mode:
                    logger.debug(f"Raw {name}")
                bangumi_data["bangumi_info"].append(data)
                logger.info(f"Adding {title_official} Season {episode.season_info.number}")

    def collect_collection(self, rss_link):
        req = self._req.get_url(rss_link)
        item = req.find("item")
        title = item.title.string
        _, data, _ = self.title_parser(title, fuzz_match=False)
        return data


if __name__ == "__main__":
    from conf.const_dev import DEV_SETTINGS
    from utils import json_config
    settings.init(DEV_SETTINGS)
    rss = RSSCollector()
    info = json_config.load("/config/bangumi.json")
    rss.collect(info)
    print(info)

