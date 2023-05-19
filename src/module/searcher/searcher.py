from .plugin import search_url
from module.network import RequestContent
from module.models import BangumiData

SEARCH_KEY = [
    "group_name",
    "title_raw",
    "season_raw",
    "subtitle",
    "source",
    "dpi",
]


class SearchTorrent(RequestContent):
    def search_torrents(self, keywords: list[str], site: str = "mikan") -> list:
        url = search_url(site, keywords)
        return self.get_torrents(url)

    def search_season(self, data: BangumiData):
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        torrents = self.search_torrents(keywords)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]