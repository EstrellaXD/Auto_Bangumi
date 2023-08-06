import logging

from module.downloader import DownloadClient
from module.models import Bangumi
from module.searcher import SearchTorrent
from module.rss import RSSEngine

logger = logging.getLogger(__name__)


class SeasonCollector(DownloadClient):
    def add_season_torrents(self, bangumi: Bangumi, torrents: list):
        return self.add_torrent(bangumi=bangumi, torrent=torrents)

    def collect_season(self, bangumi: Bangumi, link: str = None):
        logger.info(
            f"Start collecting {bangumi.official_title} Season {bangumi.season}..."
        )
        with SearchTorrent() as st:
            if not link:
                torrents = st.search_season(bangumi)
            else:
                torrents = st.get_torrents(link, _filter="|".join(bangumi.filter))
            torrent_files = None
            return self.add_season_torrents(bangumi=bangumi, torrents=torrents)

    @staticmethod
    def subscribe_season(data: Bangumi):
        with RSSEngine() as engine:
            data.added = True
            data.eps_collect = True
            engine.add_rss(
                rss_link=data.rss_link, name=data.official_title, combine=False
            )
            engine.bangumi.add(data)


def eps_complete():
    with RSSEngine() as engine:
        datas = engine.bangumi.not_complete()
        if datas:
            logger.info("Start collecting full season...")
            for data in datas:
                if not data.eps_collect:
                    with SeasonCollector() as sc:
                        sc.collect_season(data)
                data.eps_collect = True
            engine.bangumi.update_all(datas)
