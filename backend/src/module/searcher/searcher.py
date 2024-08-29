import asyncio
import json
from collections.abc import Iterable
from typing import TypeAlias

from module.conf import settings
from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.parser.title_parser import RawParser
from module.rss.engine import RSSEngine
from module.searcher.provider import search_url
from module.utils import bangumi_data

SEARCH_KEY = [
    "group_name",
    "title_raw",
    "season_raw",
    "subtitle",
    "source",
    "dpi",
]

BangumiJSON: TypeAlias = str


class SearchTorrent:
    def __init__(self) -> None:
        self.req = RequestContent

    async def search_torrents(self, rss_item: RSSItem) -> list[Torrent]:
        async with self.req() as req:
            torrents = await req.get_torrents(rss_item.url)

        new_torrents = []

        filter = "|".join(settings.rss_parser.filter)
        for torrent in torrents:
            if RSSEngine().match_torrent(torrent, bangumi=Bangumi(filter=filter)):
                new_torrents.append(torrent)
        return new_torrents

    async def analyse_keyword(
        self, keywords: list[str], site: str = "mikan", limit: int = 5
    ) -> Iterable[BangumiJSON]:
        rss_item = search_url(site, keywords)
        torrents = await self.search_torrents(rss_item)
        # yield for EventSourceResponse (Server Send)
        exist_bangumi_list: list[Bangumi] = []
        exist_list = []
        tasks = []
        bangumi_list: list[BangumiJSON] = []

        for torrent in torrents:
            new_bangumi = RawParser().parser(torrent.name)
            if new_bangumi:
                exist_str = f"{new_bangumi.title_raw}{new_bangumi.group_name}"
                if exist_str not in [
                    f"{_.title_raw}{_.group_name}" for _ in exist_bangumi_list
                ]:
                    tasks.append(
                        RSSEngine().torrent_to_data(torrent=torrent, rss=rss_item)
                    )
                    exist_bangumi_list.append(new_bangumi)

        bangumis: list[Bangumi | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        for bangumi in bangumis:
            if not isinstance(bangumi, BaseException):

                special_link = self.special_url(bangumi, site).url

                if special_link not in exist_list:
                    bangumi.rss_link = special_link
                    exist_list.append(special_link)
                    bangumi_list.append(
                        json.dumps(
                            bangumi.dict(),
                            separators=(",", ":"),
                        )
                    )
            if len(exist_list) == 5:
                break
        return iter(bangumi_list)

    @staticmethod
    def special_url(data: Bangumi, site: str) -> RSSItem:
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        url = search_url(site, keywords)
        return url

    async def search_season(self, data: Bangumi, site: str = "mikan") -> list[Torrent]:
        rss_item = self.special_url(data, site)
        torrents = await self.search_torrents(rss_item)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]


if __name__ == "__main__":
    test = Bangumi(
        official_title="【我推的孩子】",
        title_raw="Oshi No Ko",
        group_name="ANi",
        rss_link="https://mikanani.me/RSS/Bangumi?bangumiId=3407&subgroupid=583",
    )
    st = SearchTorrent()
    ans = asyncio.run(st.analyse_keyword(["败犬","ANI"]))
    for i in list(ans):
        print(i)
