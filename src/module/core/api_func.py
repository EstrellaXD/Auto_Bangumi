import re
import logging

from module.downloader import DownloadClient
from module.manager import FullSeasonGet
from module.rss import RSSAnalyser
from module.utils import json_config
from module.conf import DATA_PATH, settings
from module.models import Config
from module.network import RequestContent

from module.ab_decorator import api_failed

logger = logging.getLogger(__name__)


class APIProcess:
    def __init__(self):
        self._rss_analyser = RSSAnalyser()
        self._client = DownloadClient()
        self._full_season_get = FullSeasonGet()
        self._custom_url = settings.rss_parser.custom_url

    def link_process(self, link):
        return self._rss_analyser.rss_to_data(link)

    @api_failed
    def download_collection(self, link):
        if not self._client.authed:
            self._client.auth()
        data = self.link_process(link)
        self._full_season_get.download_collection(data, link)
        return data

    @api_failed
    def add_subscribe(self, link):
        if not self._client.authed:
            self._client.auth()
        data = self.link_process(link)
        self._client.add_rss_feed(link, data.official_title)
        self._client.set_rule(data, link)
        return data

    @staticmethod
    def reset_rule():
        data = json_config.load(DATA_PATH)
        data["bangumi_info"] = []
        json_config.save(DATA_PATH, data)
        return "Success"

    @staticmethod
    def remove_rule(_id: int):
        datas = json_config.load(DATA_PATH)["bangumi_info"]
        for data in datas:
            if data["id"] == _id:
                datas.remove(data)
                break
        json_config.save(DATA_PATH, datas)
        return "Success"

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

    @staticmethod
    def update_config(config: Config):
        settings.load()
        return {"message": "Success"}

    @staticmethod
    def get_config() -> dict:
        return settings.dict()

    def get_rss(self, full_path: str):
        url = f"https://mikanani.me/RSS/{full_path}"
        custom_url = self._custom_url
        if "://" not in custom_url:
            custom_url = f"https://{custom_url}"
        with RequestContent() as request:
            content = request.get_html(url)
        return re.sub(r"https://mikanani.me", custom_url, content)

    @staticmethod
    def get_torrent(full_path):
        url = f"https://mikanani.me/Download/{full_path}"
        with RequestContent() as request:
            return request.get_content(url)
