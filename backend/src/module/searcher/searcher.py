import json

from module.models import Bangumi, Torrent
from module.network import RequestContent
from module.rss import RSSAnalyser

from module.searcher.plugin import search_url

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
        self, keywords: list[str], site: str = "mikan", limit: int = 5
    ) -> list[Torrent]:
        url = search_url(site, keywords)
        torrents = self.get_torrents(url, limit=limit)
        return torrents

    def analyse_keyword(self, keywords: list[str], site: str = "mikan"):
        bangumis = []
        torrents = self.search_torrents(keywords, site)
        # Generate a list of json
        yield "["
        for idx, torrent in enumerate(torrents):
            bangumi = self.torrent_to_data(torrent)
            if bangumi:
                yield json.dumps(bangumi.dict())
                if idx != len(torrents) - 1:
                    yield ","
        yield "]"
        # Analyse bangumis

    def search_season(self, data: Bangumi):
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        torrents = self.search_torrents(keywords)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]


if __name__ == "__main__":
    with SearchTorrent() as st:
        keywords = ["无职转生", "第二季"]
        bangumis = st.analyse_keyword(keywords)
        for bangumi in bangumis:
            print(bangumi)
