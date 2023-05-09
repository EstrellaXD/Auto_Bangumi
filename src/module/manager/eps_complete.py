import os.path
import re
import logging

from module.network import RequestContent

from module.core import DownloadClient
from module.models import BangumiData, Config
from module.database import DataOperator

logger = logging.getLogger(__name__)


class FullSeasonGet(DownloadClient):
    def __init__(self, settings: Config):
        super().__init__()
        self.SEARCH_KEY = [
            "group",
            "title_raw",
            "season_raw",
            "subtitle",
            "source",
            "dpi",
        ]
        self.CUSTOM_URL = (
            "https://mikanani.me"
            if settings.rss_parser.custom_url == ""
            else settings.rss_parser.custom_url
        )
        if "://" not in self.CUSTOM_URL:
            if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", self.CUSTOM_URL):
                self.CUSTOM_URL = f"http://{self.CUSTOM_URL}"
            self.CUSTOM_URL = f"https://{self.CUSTOM_URL}"
        self.save_path = settings.downloader.path

    def init_eps_complete_search_str(self, data: BangumiData):
        test = []
        for key in self.SEARCH_KEY:
            data_dict = data.dict()
            if data_dict[key] is not None:
                test.append(data_dict[key])
        search_str_pre = "+".join(test)
        search_str = re.sub(r"[\W_ ]", "+", search_str_pre)
        return search_str

    def get_season_torrents(self, data: BangumiData):
        keyword = self.init_eps_complete_search_str(data)
        with RequestContent() as req:
            torrents = req.get_torrents(
                f"{self.CUSTOM_URL}/RSS/Search?searchstr={keyword}"
            )
        return [torrent for torrent in torrents if data.title_raw in torrent.name]

    def collect_season_torrents(self, data: BangumiData, torrents):
        downloads = []
        for torrent in torrents:
            download_info = {
                "url": torrent.torrent_link,
                "save_path": os.path.join(
                    self.save_path, data.official_title, f"Season {data.season}"
                ),
            }
            downloads.append(download_info)
        return downloads

    def download_season(self, data: BangumiData):
        logger.info(f"Start collecting {data.official_title} Season {data.season}...")
        torrents = self.get_season_torrents(data)
        downloads = self.collect_season_torrents(data, torrents)
        for download in downloads:
            self.add_torrent(download)
        logger.info("Completed!")
        data.eps_collect = False

    def eps_complete(self):
        with DataOperator() as op:
            datas = op.get_uncompleted()
        for data in datas:
            if data.eps_collect:
                self.download_season(data)

    def download_collection(
        self, data: BangumiData, link
    ):
        with RequestContent() as req:
            torrents = req.get_torrents(link)
        downloads = self.collect_season_torrents(data, torrents)
        logger.info(f"Starting download {data.official_title} Season {data.season}...")
        for download in downloads:
            self.add_torrent(download)
        logger.info("Completed!")
