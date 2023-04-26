import os.path
import re
import logging

from module.conf import settings
from module.network import RequestContent

from module.core.download_client import DownloadClient
from module.models import BangumiData

logger = logging.getLogger(__name__)
SEARCH_KEY = ["group", "title_raw", "season_raw", "subtitle", "source", "dpi"]
CUSTOM_URL = "https://mikanani.me" if settings.rss_parser.custom_url == "" else settings.rss_parser.custom_url


class FullSeasonGet:
    def __init__(self):
        pass

    @staticmethod
    def init_eps_complete_search_str(data: BangumiData):
        test = []
        for key in SEARCH_KEY:
            data_dict = data.dict()
            if data_dict[key] is not None:
                test.append(data_dict[key])
        search_str_pre = "+".join(test)
        search_str = re.sub(r"[\W_ ]", "+", search_str_pre)
        return search_str

    def get_season_torrents(self, data: BangumiData):
        keyword = self.init_eps_complete_search_str(data)
        with RequestContent() as req:
            torrents = req.get_torrents(f"{CUSTOM_URL}/RSS/Search?searchstr={keyword}")
        return torrents

    @staticmethod
    def collect_season_torrents(data: BangumiData, torrents):
        downloads = []
        for torrent in torrents:
            download_info = {
                "url": torrent.torrent_link,
                "save_path": os.path.join(
                        settings.downloader.path,
                        data.official_title,
                        f"Season {data.season}")
            }
            downloads.append(download_info)
        return downloads

    def download_eps(self, data: BangumiData, download_client: DownloadClient):
        logger.info(f"Start collecting {data.official_title} Season {data.season}...")
        torrents = self.get_season_torrents(data)
        downloads = self.collect_season_torrents(data, torrents)
        for download in downloads:
            download_client.add_torrent(download)
        logger.info("Completed!")
        data.eps_collect = False

    def eps_complete(self, bangumi_info: list[BangumiData], download_client: DownloadClient):
        for data in bangumi_info:
            if data.eps_collect:
                self.download_eps(data, download_client)

    def download_collection(self, data: BangumiData, link, download_client: DownloadClient):
        with RequestContent() as req:
            torrents = req.get_torrents(link)
        downloads = self.collect_season_torrents(data, torrents)
        logger.info(f"Starting download {data.official_title} Season {data.season}...")
        for download in downloads:
            download_client.add_torrent(download)
        logger.info("Completed!")


