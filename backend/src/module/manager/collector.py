import logging

from module.database import Database
from module.downloader import DownloadClient
from module.models import Bangumi, ResponseModel
from module.network import RequestContent
from module.rss import RSSEngine
from module.searcher import SearchTorrent

logger = logging.getLogger(__name__)


class SeasonCollector:
    def __init__(self, client: DownloadClient):
        self.client = client

    async def collect_season(self, bangumi: Bangumi, link: str = None):
        logger.info(
            f"Start collecting {bangumi.official_title} Season {bangumi.season}..."
        )
        st = SearchTorrent()
        if not link:
            torrents = await st.search_season(bangumi)
        else:
            async with RequestContent() as req:
                torrents = await req.get_torrents(
                    link, bangumi.filter.replace(",", "|")
                )
        with Database() as db:
            engine = RSSEngine(db)
            if await self.client.add_torrent(torrents, bangumi):
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
    async def subscribe_season(data: Bangumi, parser: str = "mikan"):
        with Database() as db:
            engine = RSSEngine(db)
            data.added = True
            data.eps_collect = True
            await engine.add_rss(
                rss_link=data.rss_link,
                name=data.official_title,
                aggregate=False,
                parser=parser,
            )
            result = await engine.download_bangumi(data)
            engine.bangumi.add(data)
            return result


async def eps_complete():
    with Database() as db:
        engine = RSSEngine(db)
        datas = engine.bangumi.not_complete()
        if datas:
            logger.info("Start collecting full season...")
            async with DownloadClient() as client:
                collector = SeasonCollector(client)
                for data in datas:
                    if not data.eps_collect:
                        await collector.collect_season(data)
                    data.eps_collect = True
            engine.bangumi.update_all(datas)
