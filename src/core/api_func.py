import re

from core import FullSeasonGet, DownloadClient, RSSAnalyser
from utils import json_config
from conf import settings

from ab_decorator import api_failed


class APIProcess:
    def __init__(self):
        self._rss_analyser = RSSAnalyser()
        self._download_client = DownloadClient()
        self._full_season_get = FullSeasonGet()

    def link_process(self, link):
        data = self._rss_analyser.rss_to_data(link)
        return data

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
        data = json_config.load(settings.info_path)
        data["bangumi_info"] = []
        json_config.save(settings.info_path, data)
        return "Success"

    @staticmethod
    def remove_rule(name):
        datas = json_config.load(settings.info_path)["bangumi_info"]
        for data in datas:
            if re.search(name.lower(), data["title_raw"].lower()):
                datas.remove(data)
                json_config.save(settings.info_path, datas)
                return "Success"
        return "Not matched"

    @staticmethod
    def add_rule(title, season):
        data = json_config.load(settings.info_path)
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
        json_config.save(settings.info_path, data)
        return "Success"


if __name__ == '__main__':
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    API = APIProcess()
    API.add_subscribe("http://dmhy.org/topics/rss/rss.xml?keyword=彻夜之歌+星空+简")