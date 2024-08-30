import asyncio
import logging
import re

from module.database import Database, engine
from module.downloader import DownloadQueue
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent
from module.parser import RawParser, TmdbParser
from module.rss.analyser import RSSAnalyser

logger = logging.getLogger(__name__)


class RSSEngine:

    def __init__(self, _engine=engine) -> None:
        self.engine = _engine
        self.queue = DownloadQueue()

    def get_active_rss(self):
        with Database(self.engine) as database:
            return database.rss.search_active()

    @staticmethod
    async def _get_torrents(rss: RSSItem) -> list[Torrent]:
        async with RequestContent() as req:
            torrents = await req.get_torrents(rss.url)
        # Add RSS ID
        if rss.id is not None:
            for torrent in torrents:
                torrent.rss_id = rss.id
        return torrents

    async def pull_rss(
        self,
        rss_item: RSSItem,
    ) -> list[Torrent]:
        """
        Retrieve all torrents that haven’t been renamed or downloaded.
        """
        torrents = await self._get_torrents(rss_item)
        with Database(self.engine) as database:
            new_torrents = database.torrent.check_new(torrents)
            return new_torrents

    def match_torrent(
        self,
        torrent: Torrent,
        rss_item: RSSItem | None = None,
        bangumi: Bangumi | None = None,
    ) -> Bangumi | None:
        """
        torrent to bangumi
        """
        matched_bangumi = bangumi
        if not matched_bangumi and rss_item:
            with Database(self.engine) as database:
                matched_bangumi = database.bangumi.match_torrent(
                    torrent_name=torrent.name,
                    rss_link=rss_item.url,
                    aggrated=rss_item.aggregate,
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
    ):
        task = []
        rss_items = self.get_active_rss()
        # From RSS Items, get all torrents
        for rss_item in rss_items:
            task.append(self.refresh_rss(rss_item.id))
        await asyncio.gather(*task)

    async def refresh_rss(
        self,
        rss_id: int,
        rss_item: RSSItem | None = None,
    ):
        # 单个的刷新rss,
        if rss_item is None:
            with Database(self.engine) as database:
                rss_item = database.rss.search_id(rss_id)
            # From RSS Items, get all torrents
        logger.debug(f"[Engine] Start refresh {rss_item.name} RSS link {rss_item.url}")
        torrent_items = await self.rss_to_data(rss_item)
        new_torrent_items: list[Torrent] = []
        for torrent in torrent_items:
            bangumi_item = self.match_torrent(torrent, rss_item)
            if bangumi_item:
                logger.debug(f"[Engine] Add torrent {torrent.name} to client")
                self.queue.add(torrent=torrent, bangumi=bangumi_item)
                new_torrent_items.append(torrent)
        logging.info(
            f"[Engine] {rss_item.name}{rss_item.url} parserd succeed, found {len(torrent_items)} new torrents, add {len(new_torrent_items)} torrents"
        )
        return torrent_items

    async def download_bangumi(self, bangumi: Bangumi,delete = False):
        """subscrib

        Args:
            bangumi: [TODO:description]

        Returns:
            [TODO:return]
        """
        # 手动写标题无Poster
        # 先抓一下poster_link, 然后save, refresh_rss
        if bangumi.poster_link is None:
            try:
                await TmdbParser.poster_parser(bangumi)
            except Exception:
                logging.warning(
                    f"[Engine] Fail to pull poster {bangumi.official_title} "
                )
        with Database(engine) as database:
            database.bangumi.add(bangumi)
            rss_item = database.rss.search_url(bangumi.rss_link)
        if not rss_item:
            rss_item = RSSItem(name=bangumi.official_title, url=bangumi.rss_link)
        await self.refresh_rss(0, rss_item=rss_item)
        if delete:
            with Database(engine) as database:
                bangumi.deleted=True
                database.bangumi.update(bangumi)
        return True

    async def torrents_to_data(
        self, torrents: list[Torrent], rss: RSSItem
    ) -> list[Bangumi]:
        """
        return new bangumi list
        """
        new_data = []
        tasks = []
        for torrent in torrents:
            bangumi = RawParser().parser(raw=torrent.name)
            # 对torrents进行一个去重, 重复的raw_name就不转了
            if bangumi and bangumi.title_raw not in [_.title_raw for _ in new_data]:
                tasks.append(
                    RSSAnalyser.official_title_parser(
                        bangumi=bangumi, rss=rss, torrent=torrent
                    )
                )
                bangumi.rss_link = rss.url
                new_data.append(bangumi)
                logger.info(f"[RSS] New bangumi founded: {bangumi.official_title}")
        # TODO: 这里可以对返回值处理下然后去掉一些没有parser成功的
        await asyncio.gather(*tasks)
        return new_data

    async def torrent_to_data(self, torrent: Torrent, rss: RSSItem) -> Bangumi | None:
        bangumi = RawParser().parser(raw=torrent.name)
        if bangumi and bangumi.official_title != "official_title":
            await RSSAnalyser.official_title_parser(
                bangumi=bangumi, rss=rss, torrent=torrent
            )
            bangumi.rss_link = rss.url
            return bangumi

    async def rss_to_data(self, rss: RSSItem) -> list[Torrent]:
        """fetch rss and add new bangumi"""
        rss_torrents = await self.pull_rss(rss)
        with Database(self.engine) as database:
            torrents_not_added = database.bangumi.match_list(
                rss_torrents,
                rss.url,
                aggrated=rss.aggregate,
            )
            if not torrents_not_added:
                logger.debug("[RSS] No new title has been found.")
            # New List
            else:
                new_data = await self.torrents_to_data(torrents_not_added, rss)
                if new_data:
                    # Add to database
                    for data in new_data:
                        database.bangumi.add(data)
        return rss_torrents

    async def link_to_data(self, rss: RSSItem) -> Bangumi | ResponseModel:
        torrents = await self.pull_rss(rss)
        if not torrents:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en="Cannot find any torrent.",
                msg_zh="无法找到种子。",
            )
        # 只有非聚合才会用
        for torrent in torrents:
            data = await self.torrent_to_data(torrent, rss)
            if data:
                return data

        return ResponseModel(
            status=False,
            status_code=406,
            msg_en="Cannot parse this link.",
            msg_zh="无法解析此链接。",
        )


if __name__ == "__main__":
    t = RSSEngine()
    tb = Bangumi(
        rss_link="https://mikanani.me/RSS/Bangumi?bangumiId=3388&subgroupid=370",
        poster_link="1",
    )
    ans = asyncio.run(t.download_bangumi(tb))
    print(ans)
