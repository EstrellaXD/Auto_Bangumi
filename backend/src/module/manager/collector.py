import logging

from module.downloader import DownloadClient
from module.models import Bangumi, ResponseModel
from module.rss import RSSEngine
from module.searcher import SearchTorrent

logger = logging.getLogger(__name__)


class SeasonCollector(DownloadClient):
    def collect_season(self, bangumi: Bangumi, link: str = None):
        logger.info(
            f"Start collecting {bangumi.official_title} Season {bangumi.season}..."
        )
        with SearchTorrent() as st, RSSEngine() as engine:
            if not link:
                torrents = st.search_season(bangumi)
            else:
                torrents = st.get_torrents(link, bangumi.filter.replace(",", "|"))
            # 去除重复的种子
            new_torrents = []
            save_path_list = []
            for item in torrents:
                if(item.save_path in save_path_list):
                    continue
                torrents_info = engine.torrent.search_finished(item.save_path)
                if(not torrents_info):
                    new_torrents.append(item)
                    save_path_list.append(item.save_path)
            if self.add_torrent(new_torrents, bangumi):
                logger.info(
                    f"Collections of {bangumi.official_title} Season {bangumi.season} completed."
                )
                for torrent in torrents:
                    torrent.downloaded = True
                bangumi.eps_collect = True
                if engine.bangumi.update(bangumi):
                    engine.bangumi.add(bangumi)
                engine.torrent.add_all(torrents)
                return ResponseModel(
                    status=True,
                    status_code=200,
                    msg_en=f"Collections of {bangumi.official_title} Season {bangumi.season} completed.",
                    msg_zh=f"收集 {bangumi.official_title} 第 {bangumi.season} 季完成。",
                )
            else:
                logger.warning(
                    f"Already collected {bangumi.official_title} Season {bangumi.season}."
                )
                return ResponseModel(
                    status=False,
                    status_code=406,
                    msg_en=f"Collection of {bangumi.official_title} Season {bangumi.season} failed.",
                    msg_zh=f"收集 {bangumi.official_title} 第 {bangumi.season} 季失败, 种子已经添加。",
                )

    @staticmethod
    def subscribe_season(data: Bangumi):
        with RSSEngine() as engine:
            data.added = True
            data.eps_collect = True
            engine.add_rss(
                rss_link=data.rss_link, name=data.official_title, aggregate=False
            )
            result = engine.download_bangumi(data)
            engine.bangumi.add(data)
            return result


def eps_complete():
    with RSSEngine() as engine:
        datas = engine.bangumi.not_complete()
        if datas:
            logger.info("Start collecting full season...")
            for data in datas:
                if not data.eps_collect:
                    with SeasonCollector() as collector:
                        collector.collect_season(data)
                data.eps_collect = True
            engine.bangumi.update_all(datas)
