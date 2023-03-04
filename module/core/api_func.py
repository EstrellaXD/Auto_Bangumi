import re

from module.core import FullSeasonGet, DownloadClient, RSSAnalyser
from module.utils import json_config
from module.conf import DATA_PATH

from module.ab_decorator import api_failed


class APIProcess:
    def __init__(self):
        self._rss_analyser = RSSAnalyser()
        self._download_client = DownloadClient()
        self._full_season_get = FullSeasonGet()

    def link_process(self, link):
        return self._rss_analyser.rss_to_data(link)

    @api_failed
    def download_collection(self, link):
        data = self.link_process(link)
        self._full_season_get.download_collection(data, link, self._download_client)
        return data

    @api_failed
    def add_subscribe(self, link):
        data = self.link_process(link)
        self._download_client.add_rss_feed(link, data.get("official_title"))
        self._download_client.set_rule(data, link)
        return data

    @staticmethod
    def reset_rule():
        data = json_config.load(DATA_PATH)
        data["bangumi_info"] = []
        json_config.save(DATA_PATH, data)
        return "Success"

    @staticmethod
    def remove_rule(name):
        datas = json_config.load(DATA_PATH)["bangumi_info"]
        for data in datas:
            if re.search(name.lower(), data["title_raw"].lower()):
                datas.remove(data)
                json_config.save(DATA_PATH, datas)
                return "Success"
        return "Not matched"

    @staticmethod
    def add_rule(title, season):
        data = json_config.load(DATA_PATH)
        extra_data = {
            "official_title": title,
            "title_raw": title,
            "season": season,
            "season_raw": "",
            "dpi": "",
            "group": "",
            "eps_complete": False,
            "added": False,
        }
        data["bangumi_info"].append(extra_data)
        json_config.save(DATA_PATH, data)
        return "Success"