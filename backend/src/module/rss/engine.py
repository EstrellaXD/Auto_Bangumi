import asyncio
import logging
import re

from module.database import Database, engine
from module.downloader import DownloadClient
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent
from module.parser import TmdbParser
from module.rss.analyser import RSSAnalyser

logger = logging.getLogger(__name__)


class RSSEngine:

    def __init__(self,_engine = engine) -> None:
        self.engine = _engine
    
    def get_active_rss(self):
        with Database(self.engine) as database:
            return database.rss.search_active()

    # async def torrent_match_bangumi(
    #     self, torrent_items: list[Torrent], rss_item: RSSItem
    # ):
    #     bangumi_item = None
    #     if rss_item.aggregate:
    #         for torrent_item in torrent_items:
    #             bangumi_item = self.match_torrent(torrent_item, rss_item )
    #     else:
    #         bangumi_item = self.search_url(rss_item.url)
    #     # 聚合没匹配到 或者 bangumi_url 没有对应的 bangumi
    #     if not bangumi_item:
    #         new_bangumi = await RSSAnalyser().torrents_to_data(torrent_items, rss_item)
    #         bangumi_item = new_bangumi
    #     return bangumi_item

    @staticmethod
    async def _get_torrents(rss: RSSItem) -> list[Torrent]:
        async with RequestContent() as req:
            torrents = await req.get_torrents(rss.url)
            # Add RSS ID
        for torrent in torrents:
            torrent.rss_id = rss.id
        return torrents

    async def pull_rss(
        self,
        rss_item: RSSItem,
        # database: Database,
        **kwargs,
    ) -> list[Torrent]:
        torrents = await self._get_torrents(rss_item)
        with Database(self.engine) as database:
            new_torrents = database.torrent.check_new(torrents)
            return new_torrents


    def search_url(self,url:str):
        with Database(self.engine) as database:
            return database.bangumi.search_url(url)



    # @staticmethod
    def match_torrent(self,
        torrent: Torrent, rss_item: RSSItem
        # , database: Database
    ) -> Bangumi | None:
        """
        torrent to bangumi
        """
        with Database(self.engine) as database:
            matched_bangumi = database.bangumi.match_torrent(
                torrent.name, rss_item.url, aggrated=rss_item.aggregate
        )

        if matched_bangumi:
            if matched_bangumi.filter == "":
                return matched_bangumi
            _filter = matched_bangumi.filter.replace(",", "|")
            if not re.search(_filter, torrent.name, re.IGNORECASE):
                torrent.bangumi_id = matched_bangumi.id
                return matched_bangumi
        return None


    async def refresh_all_rss(
        self,
        download_client:DownloadClient,
    ):

        task = []
        rss_items = self.get_active_rss()
            # From RSS Items, get all torrents
        for rss_item in rss_items:
            task.append(self.refresh_rss(download_client,rss_item.id))
        await asyncio.gather(*task)
                



    async def refresh_rss(
        self,
        download_client: DownloadClient,
        rss_id: int,
    ):

        # 单个的刷新rss,
        # Connect to Database if not connected
        with Database(self.engine) as database:
            rss_item = database.rss.search_id(rss_id)
            # From RSS Items, get all torrents
            logger.debug(f"[Engine] Start refresh {rss_item.name} RSS link {rss_item.url}")
            torrent_items = await self.pull_rss(
                rss_item=rss_item,
            )

            logging.info(f"[Engine] {rss_item.url} parserd succeed, found {len(torrent_items)} new torrents ")
            download_tasks = []
            for torrent in torrent_items:
                bangumi_item = self.match_torrent(torrent,rss_item )
                if bangumi_item:
                    logger.debug(f"[Engine] Add torrent {torrent.name} to client")
                    download_tasks.append(download_client.add_torrents([torrent],bangumi=bangumi_item))
            results = await asyncio.gather(*download_tasks,return_exceptions=True)

            for torrent,result in zip(torrent_items[:],results):
                if isinstance(result,Exception) or not result:
                    torrent_items.remove(torrent)

            database.torrent.add_all(torrent_items)
            # Close Database if not connected
        return torrent_items

    @staticmethod
    async def download_bangumi(bangumi: Bangumi):
        # 手动写标题无Poster
        if bangumi.poster_link is None:
            try:
                await TmdbParser.poster_parser(bangumi)
            except Exception:
                logging.warning(f"[Engine] Fail to pull poster {bangumi.official_title} ")
        with Database(engine) as database:
            database.bangumi.add(bangumi)

        async with RequestContent() as req:
            torrents = await req.get_torrents(
                bangumi.rss_link, bangumi.filter.replace(",", "|")
            )
            for torrent in torrents:
                torrent.bangumi_id = bangumi.id
        if torrents:
            async with DownloadClient() as client:
                await client.add_torrents(torrents, bangumi)
                with Database(engine) as database:
                    database.torrent.add_all(torrents)
                return ResponseModel(
                    status=True,
                    status_code=200,
                    msg_en=f"[Engine] Download {bangumi.official_title} successfully.",
                    msg_zh=f"下载 {bangumi.official_title} 成功。",
                )
        else:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en=f"[Engine] Download {bangumi.official_title} failed.",
                msg_zh=f"[Engine] 下载 {bangumi.official_title} 失败。",
            )

