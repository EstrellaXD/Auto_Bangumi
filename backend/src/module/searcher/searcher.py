import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from module.conf import settings
from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.parser.title_parser import MikanParser, RawParser
from module.rss import RSSAnalyser, RSSEngine
from module.searcher.mikan import MikanSearch
from module.searcher.provider import search_url

logger = logging.getLogger(__name__)


SEARCH_KEY = [
    "group_name",
    "title_raw",
    "season_raw",
    "subtitle",
    "source",
    "dpi",
]


class SearchTorrent:
    def __init__(self) -> None:
        self.req = RequestContent()
        self.analyser = RSSAnalyser()
        self.mikan_parser = MikanParser()

    async def search_torrents(self, rss_item: RSSItem) -> list[Torrent]:
        async with RequestContent() as req:
            new_torrents = await req.get_torrents(rss_item.url)

        torrents = []
        if not new_torrents:
            return []
        bangumi = RawParser().parser(new_torrents[0].name)
        if not bangumi:
            return []
        for torrent in new_torrents:
            if self.analyser.filter_torrent(torrent, bangumi):
                torrents.append(torrent)
        logger.debug(f"[SearchTorrent] Found {len(torrents)} torrents for {rss_item.url}")
        return torrents

    async def analyse_keyword(
        self, keywords: list[str], site: str = "mikan", limit: int = 7
    ) -> AsyncGenerator[dict[str, str], None]:
        rss_item = search_url(site, keywords)  # 2s
        torrents = await self.search_torrents(rss_item)
        exist_list = []
        tasks = []
        single_torrent = []

        for torrent in torrents:
            if len(exist_list) >= limit:
                break
            if new_bangumi := RawParser().parser(torrent.name,True):
                # 检查是否已经存在, 对于一个 bangumi 来说, 组,动漫,季一致就可以认为是一个
                new_str = f"{new_bangumi.title_raw}{new_bangumi.group_name}{new_bangumi.season_raw}"
                if new_str not in exist_list:
                    if torrent.homepage:
                        # 对于 mikan , 有一个 homepage, 有的话改用 mikan 的 homepage 搜索
                        single_torrent.append(torrent)
                    else:
                        task = asyncio.create_task(self.analyser.torrent_to_bangumi(torrent, rss_item))
                        tasks.append(task)
                    exist_list.append(new_str)

        logger.debug(f"[SearchTorrent] Found {len(single_torrent)} single torrents for {rss_item.url}")
        homepage_list = []
        page_task = []
        for torrent in single_torrent[:3]:
            # 取前三个 torrent 分析主页
            page_task.append(asyncio.create_task(self.mikan_parser.bangumi_link_parser(torrent.homepage)))
        logger.debug(f"[SearchTorrent] Found {len(page_task)} homepage tasks for {rss_item.url}")
        while page_task:
            done, page_task = await asyncio.wait(page_task, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                homepage = await task
                if homepage:
                    if homepage not in homepage_list:
                        homepage_list.append(homepage)
                        tasks.append(asyncio.create_task(MikanSearch(url=homepage).search()))
                    else:  # 有两个相同的主页, 就停止
                        break
        logger.debug(f"[SearchTorrent] Found {len(tasks)} tasks for {rss_item.url}")
        # 上面花了3s
        while tasks:
            done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    bangumi = await task
                    if isinstance(bangumi, list):
                        # 逆序
                        for b in bangumi[::-1]:
                            logger.debug(f"[SearchTorrent] Found bangumi: {b}")
                            yield {
                                "event": "message",
                                "data": json.dumps(b.model_dump(), separators=(",", ":")),
                            }
                    else:
                        special_link = self.special_url(bangumi, site).url
                        if special_link not in exist_list:
                            bangumi.rss_link = special_link
                            exist_list.append(special_link)

                            yield {
                                "event": "message",
                                "data": json.dumps(bangumi.model_dump(), separators=(",", ":")),
                            }
                except Exception:
                    logger.exception("[SearchTorrent] Error occurred while processing task")
        # 上面花了 5s

    def special_url(self, data: Bangumi, site: str) -> RSSItem:
        """
        根据 bangumi 的属性, 生成一个 rss_item
        """
        keywords = self.special_keyword(data)
        url = search_url(site, keywords)
        return url

    def special_keyword(self, data: Bangumi) -> list[str]:
        """
        根据 bangumi 的属性, 生成一个关键字列表
        """
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        return keywords


if __name__ == "__main__":
    import asyncio

    import pyinstrument

    async def main():
        p = pyinstrument.Profiler()
        with p:
            async for result in SearchTorrent().analyse_keyword(["败犬"], site="mikan"):
                print(json.loads(result["data"]))
        p.print()

    asyncio.run(main())
