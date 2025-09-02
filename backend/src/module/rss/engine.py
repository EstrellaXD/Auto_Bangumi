import asyncio
import logging

from sqlalchemy import Engine

from module.database import Database, engine
from module.downloader import DownloadQueue, download_queue
from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.parser import RawParser
from module.rss.analyser import RSSAnalyser

logger = logging.getLogger(__name__)


class BaseRefresh:
    def __init__(self, _engine=engine):
        self.engine = _engine
        self.url: str = ""

    async def _get_torrents(self) -> list[Torrent]:
        # 拉取 rss_item 对应的 未下载掉 torrents
        async with RequestContent() as req:
            torrents = await req.get_torrents(self.url)
        logging.debug(f"[RSS ENGINE] from {self.url} get {len(torrents)}")
        with Database(self.engine) as database:
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


class RSSRefresh(BaseRefresh):
    def __init__(self, rss_item: RSSItem, _engine=engine):
        super().__init__(_engine)
        self.rss_item: RSSItem = rss_item
        self.bangumis: list[Bangumi] = []
        self.url: str = rss_item.url
        self.bangumi: Bangumi | None = None
        self.analyser: RSSAnalyser = RSSAnalyser()
        self.download_queue: DownloadQueue = download_queue

    async def download_rss(self) -> list[Torrent]:
        """下载 rss_item 对应的 torrents"""
        torrents = await self.pull_rss()
        for torrent in torrents:
            raw_bangumi = RawParser().parser(raw=torrent.name)
            if raw_bangumi:
                # 这里可以直接用 raw_bangumi.title_raw 来查找 bangumi
                with Database(self.engine) as database:
                    bangumi = database.find_bangumi_by_name(
                        raw_bangumi.title_raw,
                        self.rss_item.url,
                        self.rss_item.aggregate,
                    )
                    if not bangumi:
                        logger.debug(f"[RSS download_rss] No bangumi found for {raw_bangumi.title_raw}")
                    elif not bangumi.deleted and self.analyser.filter_torrent(torrent, bangumi):
                        ## 如果不符合过滤条件, 则跳过
                        self.download_queue.add(torrent, bangumi)
                        logger.debug(
                            f"[RSS download_rss] Find bangumi {bangumi.official_title} by torrent {torrent.name}"
                        )

        logger.debug(f"[RSS download_rss] pull {len(torrents)} torrents from {self.rss_item.url}")
        return torrents

    async def find_new_bangumi(self, add_to_db: bool = True) -> list[Bangumi]:
        # 先获取 全部的 torrents
        # 整个的流程可分为两部, 1. 刷新 bangumi 2. 刷新 torrents,可以解决一下清空后 bangumi 一直没有的问题
        # 现在完成第一步,
        # 1. 拉取所有的 torrents
        # 2. 看看在数据库中有没有对应的 bangumi, 如果没有, 对 torrents 进行解析
        # 3. 如果有 bangumi
        # TODO: 给魂酱加个开关, 不加入被默认过滤的动漫
        # torrents = await self.pull_rss()

        async with RequestContent() as req:
            torrents = await req.get_torrents(self.url)
        logger.debug(f"[RSS] pull {len(torrents)} torrents from {self.url}")
        new_torrents = {}
        for torrent in torrents:
            # 这是对于非聚合的 rss, 只对第一个处理就好了
            if self.bangumi:
                continue
            # 先从数据库中找, 如果数据库中没有, 更新一下 database
            raw_bangumi = RawParser().parser(raw=torrent.name,exclude_collection=True)
            logger.debug(f"[RSSRefresh] raw bangumi {raw_bangumi.title_raw if raw_bangumi else 'None'}")

            if raw_bangumi and self.analyser.filter_torrent(torrent, raw_bangumi):
                if new_torrents.get(raw_bangumi.title_raw):
                    # 如果已经有了, 则跳过
                    logger.debug(f"[RSSRefresh] {raw_bangumi.title_raw} already in new_torrents")
                    continue
                else:
                    with Database(engine) as database:
                        bangumi = database.find_bangumi_by_name(
                            raw_bangumi.title_raw, self.rss_item.url, self.rss_item.aggregate
                        )
                        if bangumi:
                            logger.debug(
                                f"[RSSRefresh] Find bangumi {bangumi.official_title} by torrent {torrent.name}"
                            )
                        else:
                            logger.debug(f"[RssRefresh] add new torrent {torrent.name} to new_torrents")
                            new_torrents[raw_bangumi.title_raw] = torrent

        tasks = []

        logger.debug(f"[RSSRefresh] Found {len(new_torrents)} new torrents to parse.")
        for _, torrent in new_torrents.items():
            task = self.analyser.torrent_to_bangumi(torrent=torrent, rss=self.rss_item)
            tasks.append(task)
        bangumis = await asyncio.gather(*tasks)
        for bangumi in bangumis:
            with Database(engine) as db:
                # 如果没有mikan_id 和 bangumi_id 则不加入数据库
                if bangumi and (bangumi.mikan_id or bangumi.tmdb_id):
                    logger.debug(f"[RSSRefresh] Parsed bangumi: {bangumi.official_title} add to database")
                    db.bangumi.add(bangumi)


class BangumiRefresher(BaseRefresh):
    def __init__(self, bangumi: Bangumi, _engine=engine):
        super().__init__(_engine)
        self.bangumi: Bangumi = bangumi
        self.url: str = bangumi.rss_link
        self.analyser = RSSAnalyser()
        self.download_queue: DownloadQueue = download_queue

    async def refresh(self) -> list[Torrent]:
        """刷新 bangumi 的 rss"""
        torrents = await self.pull_rss()
        new_torrents = []
        for torrent in torrents:
            if self.analyser.filter_torrent(torrent, self.bangumi):
                logger.debug(
                    f"[BangumiRefresher] Add torrent {torrent.name} to download queue for bangumi {self.bangumi.official_title}"
                )
                # 这里是最早加入 torrent.bang
                new_torrents.append(torrent)

        logger.debug(f"[BangumiRefresher] Found {len(new_torrents)} new torrents for {self.bangumi.official_title}")
        return new_torrents


# 对一个 rss_item 做一个假设, 认为一个 rss_link 里面 一部动漫只有一季
# 由于无法知道当前的 rss 里面是否 bangumi 是否在,所以单个 rss 中能线性处理
# 这样 相同的 official_title 就可以认为是一个动漫, 用 official_title 作为 key
# 对于 collect and subscribe , 只有 bangumi, 唯一的区别是 subscribe 会 add 到 database
# 日常的是只有 rss_item, 没有 bangumi
# 整体流程是, 先拉取 rss_item 对应的 torrents
# 如果 self.bangumi 为空, 则去 database 中找, 如果 database 中没有, 则进行一次解析
# 如果 self.bangumi 不为空, 则将 torrents 放到 bangumi_torrents 中, 对应为 搜索, 订阅, 收集, 非聚合
#     会用到 rss 的地方一共有 3 个
#     1. 日常的刷新, 这时候只有 rss_item, 没有 bangumi
#     2. 订阅, 这时候没有 rss_item, 有 bangumi
#     3. 收集, 这时候没有 rss_item, 有 bangumi,但 不把 bangumi 放到 database 中
#     4. eps, 有 rss_item, 有 bangumi
#     5. 搜索, 有 rss_item


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

    9. 主要是用于整体刷新, 小的 eps 之类的用 RssRefresh

    10. 聚合的要先更新一遍到 database 中

    """

    def __init__(self, _engine=engine) -> None:
        self.engine: Engine = _engine
        self.queue: DownloadQueue = download_queue

    def get_active_rss(self) -> list[RSSItem]:
        """获取所有活跃的rss"""
        with Database(self.engine) as database:
            rss_items = database.rss.search_active()
            logger.debug(f"[RSS] get {len(rss_items)} active rss items")
        return rss_items

    async def refresh_rss(self, rss_item: RSSItem) -> None:
        rssrefresh = RSSRefresh(rss_item=rss_item)
        await rssrefresh.find_new_bangumi()
        await rssrefresh.download_rss()

    async def refresh_all(self):
        """刷新所有rss"""
        tasks = []
        rss_items = self.get_active_rss()
        for rss_item in rss_items:
            tasks.append(self.refresh_rss(rss_item))
        await asyncio.gather(*tasks)

    async def refresh_bangumi(self, bangumi: Bangumi) -> list[Torrent]:
        """刷新一个bangumi的rss, 并将其放入下载队列中"""
        logger.debug(f"[RSSEngine] refresh bangumi {bangumi.official_title}")
        refresher = BangumiRefresher(bangumi=bangumi)
        torrents = await refresher.refresh()
        if not torrents:
            logger.debug(f"[RSSEngine] No torrents found for {bangumi.official_title}")
            return []
        return torrents

    async def download_bangumi(self, bangumi: Bangumi) -> bool:
        """下载一个bangumi的rss, 并将其放入下载队列中"""
        logger.debug(f"[RSSEngine] download bangumi {bangumi.official_title}")
        torrents = await self.refresh_bangumi(bangumi)
        if not torrents:
            logger.debug(f"[RSSEngine] No torrents found for {bangumi.official_title}")
            return False
        await self.queue.add_torrents(torrents, bangumi)
        return True


if __name__ == "__main__":
    from module.conf import setup_logger

    setup_logger("DEBUG")

    async def test():
        test_rss = RSSItem(
            url="https://mikanani.me/RSS/Bangumi?bangumiId=3659&subgroupid=382",
            parser="mikan",
            aggregate=True,
        )
        test_refresh = RSSRefresh(rss_item=test_rss)
        await test_refresh.find_new_bangumi()
        await test_refresh.download_rss()

    asyncio.run(test())
