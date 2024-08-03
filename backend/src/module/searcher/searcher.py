import asyncio
import json
from typing import TypeAlias

from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.rss import RSSAnalyser
from module.searcher.provider import search_url

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
            return await req.get_torrents(rss_item.url)
        # torrents = self.get_torrents(rss_item.url)
        # return torrents

    async def analyse_keyword(
        self, keywords: list[str], site: str = "mikan", limit: int = 5
    ) -> list[BangumiJSON]:
        rss_item = search_url(site, keywords)
        torrents = await self.search_torrents(rss_item)
        # yield for EventSourceResponse (Server Send)
        exist_list = []
        tasks = []
        bangumi_list = []
        for torrent in torrents[:20]:
            tasks.append(RSSAnalyser().torrent_to_data(torrent=torrent, rss=rss_item))
        bangumis = await asyncio.gather(*tasks, return_exceptions=True)
        for bangumi in bangumis:
            if bangumi:
                special_link = self.special_url(bangumi, site).url
                if special_link not in exist_list:
                    exist_list.append(special_link)
                    bangumi.rss_link = special_link
                    exist_list.append(special_link)
                    bangumi_list.append(
                        json.dumps(bangumi.dict(), separators=(",", ":"))
                    )
                    if len(exist_list) == 5:
                        break
        return iter(bangumi_list)

    @staticmethod
    def special_url(data: Bangumi, site: str) -> RSSItem:
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        print(f"{keywords=}")
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
    print(asyncio.run(st.search_season(test)))
