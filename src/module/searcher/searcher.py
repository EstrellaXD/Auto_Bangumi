from .plugin import search_url
from module.network import RequestContent


class SearchTorrent(RequestContent):
    def search_torrents(self, keywords: list[str], site: str = "mikan") -> list:
        url = search_url(site, keywords)
        return self.get_torrents(url)