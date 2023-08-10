import logging

from module.downloader import DownloadClient
from module.models import Bangumi
from module.searcher import SearchTorrent
from module.rss import RSSEngine

logger = logging.getLogger(__name__)


class SeasonCollector(DownloadClient):
    def collect_season(self, bangumi: Bangumi, link: str = None):
        logger.info(
            f"Start collecting {bangumi.official_title} Season {bangumi.season}..."
        )
        with SearchTorrent() as st:
            if not link:
                torrents = st.search_season(bangumi)
            else:
                torrents = st.get_torrents(link, _filter="|".join(bangumi.filter))
            return self.add_torrent(torrents, bangumi)

    def subscribe_season(self, data: Bangumi):
        with RSSEngine() as engine:
            data.added = True
            data.eps_collect = True
            engine.add_rss(
                rss_link=data.rss_link, name=data.official_title, combine=False
            )
            engine.bangumi.add(data)
            engine.refresh_rss(self)


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
