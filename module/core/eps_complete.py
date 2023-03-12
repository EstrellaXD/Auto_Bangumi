import os.path
import re
import logging

from module.conf import settings
from module.network import RequestContent

from .download_client import DownloadClient

logger = logging.getLogger(__name__)
SEARCH_KEY = ["group", "title_raw", "season_raw", "subtitle", "source", "dpi"]


class FullSeasonGet:
    def __init__(self):
        pass

    @staticmethod
    def init_eps_complete_search_str(data: dict):
        test = [data.get(key).strip() for key in SEARCH_KEY if data.get(key) is not None]
        search_str_pre = "+".join(test)
        search_str = re.sub(r"[\W_ ]", "+", search_str_pre)
        return search_str

    def get_season_torrents(self, data: dict):
        keyword = self.init_eps_complete_search_str(data)
        with RequestContent() as req:
            torrents = req.get_torrents(f"https://mikanani.me/RSS/Search?searchstr={keyword}")
        return torrents

    @staticmethod
    def collect_season_torrents(data: dict, torrents):
        downloads = []
        for torrent in torrents:
            download_info = {
                "url": torrent.torrent_link,
                "save_path": os.path.join(
                        settings.download_path,
                        data["official_title"],
                        f"Season {data['season']}")
            }
            downloads.append(download_info)
        return downloads

    def download_eps(self, data, download_client: DownloadClient):
        logger.info(f"Start collecting {data['official_title']} Season {data['season']}...")
        torrents = self.get_season_torrents(data)
        downloads = self.collect_season_torrents(data, torrents)
        for download in downloads:
            download_client.add_torrent(download)
        logger.info("Completed!")
        data["eps_collect"] = False

    def eps_complete(self, bangumi_info, download_client: DownloadClient):
        for data in bangumi_info:
            if data["eps_collect"]:
                self.download_eps(data, download_client)

    def download_collection(self, data, link, download_client: DownloadClient):
        with RequestContent() as req:
            torrents = req.get_torrents(link)
        downloads = self.collect_season_torrents(data, torrents)
        logger.info(f"Starting download {data.get('official_title')}")
        for download in downloads:
            download_client.add_torrent(download)
        logger.info("Completed!")


if __name__ == "__main__":
    a = FullSeasonGet()
    data = {
            "official_title": "指名！",
            "title_raw": "CUE!",
            "season": 1,
            "season_raw": "",
            "group": "喵萌Production",
            "dpi": "1080p",
            "source": None,
            "subtitle": "简日双语",
            "added": True,
            "eps_collect": True
        }
    print(a.init_eps_complete_search_str(data))
