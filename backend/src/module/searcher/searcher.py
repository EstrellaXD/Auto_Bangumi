import json
from typing import TypeAlias

from module.models import Bangumi, Torrent, RSSItem
from module.network import RequestContent
from module.rss import RSSAnalyser

from .provider import search_url

SEARCH_KEY = [
    "group_name",
    "title_raw",
    "season_raw",
    "subtitle",
    "source",
    "dpi",
]

BangumiJSON: TypeAlias = str


class SearchTorrent(RequestContent, RSSAnalyser):
    def search_torrents(
        self, rss_item: RSSItem, limit: int = 5
    ) -> list[Torrent]:
        torrents = self.get_torrents(rss_item.url, limit=limit)
        return torrents

    def analyse_keyword(self, keywords: list[str], site: str = "mikan") -> BangumiJSON:
        rss_item = search_url(site, keywords)
        torrents = self.search_torrents(rss_item)
        # yield for EventSourceResponse (Server Send)
        exist_list = []
        for torrent in torrents:
            bangumi = self.torrent_to_data(torrent=torrent, rss=rss_item)
            if bangumi and bangumi not in exist_list:
                exist_list.append(bangumi)
                yield json.dumps(bangumi.dict(), separators=(',', ':'))

    def search_season(self, data: Bangumi):
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        url = search_url("mikan", keywords)
        torrents = self.search_torrents(url)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]


if __name__ == "__main__":
    with SearchTorrent() as st:
        keywords = ["无职转生", "第二季"]
        bangumis = st.analyse_keyword(keywords)
        for bangumi in bangumis:
            print(bangumi)
