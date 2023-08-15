import json

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


class SearchTorrent(RequestContent, RSSAnalyser):
    def search_torrents(
        self, rss_item: RSSItem, limit: int = 5
    ) -> list[Torrent]:
        torrents = self.get_torrents(rss_item.url, limit=limit)
        return torrents

    def analyse_keyword(self, keywords: list[str], site: str = "mikan"):
        rss_item = search_url(site, keywords)
        torrents = self.search_torrents(rss_item)
        # Generate a list of json
        yield "["
        for idx, torrent in enumerate(torrents):
            bangumi = self.torrent_to_data(torrent=torrent, rss=rss_item)
            if bangumi:
                yield json.dumps(bangumi.dict())
                if idx != len(torrents) - 1:
                    yield ","
        yield "]"

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
