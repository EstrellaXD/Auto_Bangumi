import asyncio
import json
from collections.abc import AsyncGenerator

from module.conf import settings
from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.parser.api import RemoteMikan
from module.parser.title_parser import MikanParser, RawParser
from module.rss import RSSAnalyser, RSSRefresh
from module.searcher.mikan import MikanSearch
from module.searcher.provider import search_url

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
        self.page = RemoteMikan()
        self.mikan_parser = MikanParser(page=self.page)

    async def search_torrents(self, rss_item: RSSItem) -> list[Torrent]:
        # 想了想 search 没必要有一个 Filter, 下载的时候也不会有
        # TODO: 思考这里要不要用 filter
        # 主要是想借用一下 filter, 从 rss 拿 torrents
        bangumi = Bangumi(
            exclude_filter="|".join(settings.rss_parser.filter),
            rss_link=rss_item.url,
        )
        bangumi_torrents = RSSRefresh(bangumi=bangumi)
        await bangumi_torrents.refresh()
        if bangumi.official_title in bangumi_torrents.bangumi_torrents:
            return bangumi_torrents.bangumi_torrents[bangumi.official_title].torrents
        return []

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
            if new_bangumi := BParser().parser(torrent.name):
                # 检查是否已经存在, 对于一个 bangumi 来说, 组,动漫,季一致就可以认为是一个
                new_str = f"{new_bangumi.title_raw}{new_bangumi.group_name}{new_bangumi.season_raw}"
                if new_str not in exist_list:
                    if torrent.homepage:
                        # 对于 mikan , 有一个 homepage, 有的话改用 mikan 的 homepage 搜索
                        single_torrent.append(torrent)
                    else:
                        task = asyncio.create_task(
                            self.analyser.torrent_to_bangumi(torrent, rss_item)
                        )
                        tasks.append(task)
                    exist_list.append(new_str)

        homepage_list = []
        page_task = []
        for torrent in single_torrent:
            # 取前三个 torrent 分析主页
            page_task.append(
                asyncio.create_task(
                    self.mikan_parser.bangumi_link_parser(torrent.homepage)
                )
            )
            if len(page_task) >= 3:
                break
        while page_task:
            done, page_task = await asyncio.wait(
                page_task, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                homepage = await task
                if homepage:
                    if homepage not in homepage_list:
                        homepage_list.append(homepage)
                        tasks.append(
                            asyncio.create_task(
                                MikanSearch(url=homepage, page=self.page).search()
                            )
                        )
                    else:  # 有两个相同的主页, 就停止
                        break
        # 上面花了3s
        while tasks:
            done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    bangumi = await task
                    if isinstance(bangumi, list):
                        # 逆序
                        for b in bangumi[::-1]:
                            yield {
                                "event": "message",
                                "data": json.dumps(
                                    b.model_dump(), separators=(",", ":")
                                ),
                            }
                    else:
                        special_link = self.special_url(bangumi, site).url
                        if special_link not in exist_list:
                            bangumi.rss_link = special_link
                            exist_list.append(special_link)

                            yield {
                                "event": "message",
                                "data": json.dumps(
                                    bangumi.model_dump(), separators=(",", ":")
                                ),
                            }
                except Exception:
                    continue
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
