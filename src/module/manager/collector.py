import logging

from fastapi.responses import JSONResponse

from module.downloader import DownloadClient
from module.models import BangumiData
from module.database import BangumiDatabase
from module.searcher import SearchTorrent

logger = logging.getLogger(__name__)


class SeasonCollector(DownloadClient):
    def add_season_torrents(self, data: BangumiData, torrents):
        for torrent in torrents:
            download_info = {
                "url": torrent.torrent_link,
                "save_path": self._gen_save_path(data),
            }
            self.add_torrent(download_info)

    def collect_season(self, data: BangumiData, link: str = None):
        logger.info(f"Start collecting {data.official_title} Season {data.season}...")
        with SearchTorrent() as st:
            if not link:
                torrents = st.search_season(data)
            else:
                torrents = st.get_torrents(link, _filter="|".join(data.filter))
        self.add_season_torrents(data, torrents)
        logger.info("Completed!")

    def subscribe_season(self, data: BangumiData):
        with BangumiDatabase() as db:
            data.added = True
            data.eps_collect = True
            self.set_rule(data)
            db.insert(data)
        self.add_rss_feed(data.rss_link[0], item_path=data.official_title)


def eps_complete():
    with BangumiDatabase() as bd:
        datas = bd.not_complete()
        if datas:
            logger.info("Start collecting full season...")
            for data in datas:
                if not data.eps_collect:
                    with SeasonCollector() as sc:
                        sc.collect_season(data)
                data.eps_collect = True
            bd.update_list(datas)


if __name__ == "__main__":
    from module.conf import setup_logger

    setup_logger()
    eps_complete()
