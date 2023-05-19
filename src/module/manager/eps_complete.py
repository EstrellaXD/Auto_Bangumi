import os.path
import re
import logging

from module.network import RequestContent
from module.downloader import DownloadClient
from module.models import BangumiData
from module.database import BangumiDatabase
from module.searcher import SearchTorrent
from module.conf import settings

logger = logging.getLogger(__name__)
SEARCH_KEY = [
    "group_name",
    "title_raw",
    "season_raw",
    "subtitle",
    "source",
    "dpi",
]


class FullSeasonGet(DownloadClient):
    def init_search_str(self, data: BangumiData):
        str_list = []
        for key in SEARCH_KEY:
            data_dict = data.dict()
            if data_dict[key] is not None:
                str_list.append(data_dict[key])
        return str_list

    def get_season_torrents(self, data: BangumiData):
        keywords = self.init_search_str(data)
        with SearchTorrent() as st:
            torrents = st.search_torrents(keywords)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]

    def collect_season(self, data: BangumiData, torrents):
        official_title = f"{data.official_title}({data.year})" if data.year else data.official_title
        for torrent in torrents:
            download_info = {
                "url": torrent.torrent_link,
                "save_path": os.path.join(
                    settings.downloader.path, official_title, f"Season {data.season}"
                ),
            }
            self.add_torrent(download_info)

    def download_season(self, data: BangumiData):
        logger.info(f"Start collecting {data.official_title} Season {data.season}...")
        torrents = self.get_season_torrents(data)
        self.collect_season(data, torrents)
        logger.info("Completed!")
        data.eps_collect = True

    def eps_complete(self):
        with BangumiDatabase() as bd:
            datas = bd.not_complete()
            if datas:
                logger.info("Start collecting full season...")
                for data in datas:
                    if not data.eps_collect:
                        self.download_season(data)
                bd.update_list(datas)

    def download_collection(
        self, data: BangumiData, link
    ):
        with RequestContent() as req:
            torrents = req.get_torrents(link)
        logger.info(f"Starting download {data.official_title} Season {data.season}...")
        self.collect_season(data, torrents)
        logger.info("Completed!")

    def add_subscribe(self, data: BangumiData):
        self.add_rss_feed(data.rss_link, item_path=data.official_title)
        self.set_rule(data)


if __name__ == '__main__':
    from module.conf import setup_logger
    setup_logger()
    with FullSeasonGet() as full_season_get:
        full_season_get.eps_complete()