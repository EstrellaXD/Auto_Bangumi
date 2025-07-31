import asyncio
import logging
import re
from abc import abstractmethod

from typing_extensions import override

from module.database import Database, engine
from module.downloader import DownloadQueue
from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.rss.analyser import RSSAnalyser

logger = logging.getLogger(__name__)


class RssBase:
    """
    实现一些 rss 的通用方法, 获取 rss url 对应的 torrents
    当传入 bangumi 时, 会使用 bangumi 的 rss_link 作为 url
    Attributes:
        torrent_cache (list[Torrent]): The cache of torrents.
        rss_item (RSSItem): The rss item.
        bangumi (Bangumi | None): The bangumi item.
    会用到 rss 的地方一共有 3 个
    1. 日常的刷新, 这时候只有 rss_item, 没有 bangumi
    2. 订阅, 这时候没有 rss_item, 有 bangumi
    3. 收集, 这时候没有 rss_item, 有 bangumi,但 不把 bangumi 放到 database 中
    4. eps, 有 rss_item, 有 bangumi
    5. 搜索, 有 rss_item
    当有 bangumi 时, 会使用 bangumi 的 rss_link 作为 url
    """

    def __init__(
        self,
        rss_item: RSSItem | None = None,
        bangumi: Bangumi | None = None,
        _engine=engine,
    ) -> None:
        if not rss_item and not bangumi:
            raise ValueError("rss_item and bangumi can't be None at the same time")
        self.analyser: RSSAnalyser = RSSAnalyser(_engine)
        self.rss_item = rss_item
        self.bangumi = bangumi
        self.bangumi_torrents = {}
        if self.bangumi:
            self.url: str = self.bangumi.rss_link
        if self.rss_item:
            self.url: str = self.rss_item.url
        else:
            # 如果有 bangumi 找 rss, 对应 subscribe
            if self.bangumi and not self.rss_item:
                # 从 database 中找 rss_item
                with Database(engine) as database:
                    self.rss_item = database.bangumi_to_rss(self.bangumi)
                    if not self.rss_item:
                        logger.debug(f"[RSS] No RSS found for bangumi {self.bangumi.official_title}, cannot refresh.")

    async def _get_torrents(self, url: str) -> list[Torrent]:
        async with RequestContent() as req:
            torrents = await req.get_torrents(url)
        logging.debug(f"[RSS ENGINE] from {self.url} get {len(torrents)}")
        with Database() as database:
            new_torrents = database.torrent.check_new(torrents)
        return new_torrents

    async def pull_rss(self) -> list[Torrent]:
        """拉取 rss_item 对应的 torrents"""
        torrents = await self._get_torrents(self.url)
        logger.debug(f"[RSS] pull {len(torrents)} torrents from {self.url}")
        # 这里是最早加入 torrent.rss_link 的地方
        if self.rss_item:
            for torrent in torrents:
                torrent.rss_link = self.rss_item.url
        return torrents

class BaseRefresh:
    def __init__(self):
        self.url :str = ""

    async def _get_torrents(self) -> list[Torrent]:
        async with RequestContent() as req:
            torrents = await req.get_torrents(self.url)
        logging.debug(f"[RSS ENGINE] from {self.url} get {len(torrents)}")
        with Database() as database:
            new_torrents = database.torrent.check_new(torrents)
        return new_torrents

    async def pull_rss(self) -> list[Torrent]:
        """拉取 rss_item 对应的 torrents"""
        torrents = await self._get_torrents()
        logger.debug(f"[RSS] pull {len(torrents)} torrents from {self.url}")
        # 这里是最早加入 torrent.rss_link 的地方
        if self.url:
            for torrent in torrents:
                torrent.rss_link = self.url
        return torrents

class RssRefresh(BaseRefresh):
    def __init__(self, rss_item: RSSItem):
        self.rss_item:RSSItem = rss_item
        self.bangumis:list[Bangumi] = []
        self.url:str = rss_item.url
        self.bangumi: Bangumi | None = None

    async def rss2bangumis(self,add_to_db: bool = True) -> list[Bangumi]:
        torrents = await self.pull_rss()

        for torrent in torrents:
            if self.bangumi:
                continue
            # 先从数据库中找, 如果数据库中没有, 更新一下 database
            with Database(engine) as database:
                bangumi = database.find_bangumi_by_torrent(torrent,self.rss_item.aggregate)
                if bangumi:
                    logger.debug(f"[RSS analyser] Find bangumi {bangumi.official_title} by torrent {torrent.name}")

            if not bangumi:
                bangumi = await RSSAnalyser().torrent_to_bangumi(torrent, self.rss_item)
                if bangumi and add_to_db:
                    with Database(engine) as database:
                        for bangumi in self.bangumis:
                                database.bangumi.add(bangumi)
                                logger.debug(f"[RSS] Add bangumi {bangumi.official_title} to database")
            if self.rss_item.aggregate:
                self.bangumi = bangumi


        return self.bangumis


class BangumiRefresher(BaseRefresh):
    def __init__(self, bangumi: Bangumi):
        self.bangumi: Bangumi = bangumi
        self.url: str = bangumi.rss_link
        self.exclude_filter = self.bangumi.exclude_filter.replace(",", "|") if self.bangumi.exclude_filter else ""
        self.include_filter = self.bangumi.include_filter.replace(",", "|") if self.bangumi.include_filter else ""
        self.torrents: list[Torrent] = []

    async def bangumi2torrents(self) -> list[Torrent]:
        """刷新 bangumi 的 rss"""
        torrents =await self.pull_rss()
        for torrent in torrents:
            # Check exclude filter (if matches, reject torrent)
            if self.exclude_filter and re.search(self.exclude_filter, torrent.name):
                logger.debug(f"[RSS] Exclude torrent {torrent.name} for {self.bangumi.official_title},regex: {self.exclude_filter}")
                continue
            
            # Check include filter first (if set, torrent must match)
            if self.include_filter and not re.search(self.include_filter, torrent.name):
                continue
            
            # If it passes the filters, add to bangumi's torrents
            self.torrents.append(torrent)

        return self.torrents


    

# class RSSRefresh(RssBase):
#     """
#     刷新 rss 的 torrent
#     """
#     # torrents = await self.pull_rss()
#
#     async def refresh(self) -> bool:
#         # 对一个 rss_item 做一个假设, 认为一个 rss_link 里面 一部动漫只有一季
#         # 由于无法知道当前的 rss 里面是否 bangumi 是否在,所以单个 rss 中能线性处理
#         # 这样 相同的 official_title 就可以认为是一个动漫, 用 official_title 作为 key
#         # 对于 collect and subscribe , 只有 bangumi, 唯一的区别是 subscribe 会 add 到 database
#         # 日常的是只有 rss_item, 没有 bangumi
#         # 整体流程是, 先拉取 rss_item 对应的 torrents
#         # 如果 self.bangumi 为空, 则去 database 中找, 如果 database 中没有, 则进行一次解析
#         # 如果 self.bangumi 不为空, 则将 torrents 放到 bangumi_torrents 中, 对应为 搜索, 订阅, 收集, 非聚合
#
#
#         # 到这就一定有 rss_item 了
#         if not self.rss_item:
#             logger.error("[RSS] No RSS item found, cannot refresh.")
#             return False
#
#         torrents = await self.pull_rss()
#         # 有点问题,如果下载了,但没有新的,导致一直无法刷新
#         for torrent in torrents:
#             # 如果 bangumi 为空, 更新 bangumi
#             if not self.bangumi:
#                 # 先从数据库中找, 如果数据库中没有, 更新一下 database
#                 bangumi = await self.analyser.torrent_to_bangumi(
#                     torrent, self.rss_item
#                 )
#                 if bangumi:
#                     logger.debug(f"[RSS] Parsed bangumi: {bangumi.official_title}")
#                     with Database(engine) as database:
#                         database.bangumi.add(bangumi)
#                 if bangumi:
#                     # TODO: 不一定在这更新
#                     # 这个还是要想想怎么弄, 要是没有的话就不加可能就没机会加了
#                     if not self.rss_item.aggregate:
#                         # 如果 不是聚合的, 则更新 bangumi
#                         # 这样就可以避免多余的请求
#                         self.bangumi:Bangumi = bangumi
#                     title = bangumi.official_title
#                     if title not in self.bangumi_torrents:
#                         self.bangumi_torrents[title] = TorrentBangumi(bangumi)
#                     else:
#                         # TODO: bangumi_torrents 中如果已经存在, 则更新 bangumi
#                         pass
#                     self.bangumi_torrents[title].append(torrent)
#             else:
#                 # 先抓一下poster_link, 然后save, refresh_rss
#                 if self.bangumi.official_title not in self.bangumi_torrents:
#                     self.bangumi_torrents[self.bangumi.official_title] = TorrentBangumi(
#                         self.bangumi
#                     )
#                 self.bangumi_torrents[self.bangumi.official_title].append(torrent)


class RSSEngine:
    """要完成
    1. 将 torrent_item 转为bangumi
    2. rss_item 转为 torrent_item
    3. 发送到 Download_queue
    4. torrent 找到bangumi

    5. collect 有 rss_item,无bangumi?
    collect 就更麻烦了, rss_item 是没有的,不好找bangumi, bangumi没有不好改名
    这个到是好解决, bangumi 隐藏一下到是也能用

    6. subscribe 有 rss_item,有bangumi
    subscribe 只用refresh一下自己就好了

    7. eps 有 rss_item,有bangumi
    eps 是没有 保存rss_item的,主要是eps的rss和保存的rss不一致,不好找bangumi

    放弃
    8. 一个 rss cache , dict[rss_link,list[torrent_item], 到也不用太复杂, RSS都从 Engine 拿
    内部维护一个就好了,如果有就说明这段时间请求过,

    9. 主要是用于整体刷新, 小的 eps 之类的用 RssRefresh

    10. 聚合的要先更新一遍到 database 中

    """

    def __init__(self, _engine=engine) -> None:
        self.engine = _engine
        self.queue = DownloadQueue()

    def get_active_rss(self) -> list[RSSItem]:
        """获取所有活跃的rss"""
        with Database(self.engine) as database:
            rss_items = database.rss.search_active()
            logger.debug(f"[RSS] get {len(rss_items)} active rss items")
        return rss_items

    async def refresh_all(self):
        """刷新所有rss"""
        tasks = []
        rss_items = self.get_active_rss()
        for rss_item in rss_items:
            rssrefresh = RssRefresh(rss_item=rss_item)
            tasks.append(rssrefresh.rss2bangumis())
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    from module.conf import setup_logger
    setup_logger("DEBUG")

    async def test():
        test_rss = RSSItem(
            url="https://mikanani.me/RSS/Bangumi?bangumiId=3464&subgroupid=639"
            ,parser="tmdb"
            ,aggregate=True
        )
        test_refresh = RSSRefresh(rss_item=test_rss)
        await test_refresh.refresh()

    async def test_engine():
        test_engine = RSSEngine()
        await test_engine.refresh_all()

    asyncio.run(test())
