import re

from dataclasses import dataclass
from bs4 import BeautifulSoup

from .request_url import RequestURL

from module.conf import settings


FILTER = "|".join(settings.rss_parser.filter)


@dataclass
class TorrentInfo:
    name: str
    torrent_link: str


class RequestContent(RequestURL):
    # Mikanani RSS
    def get_torrents(self, _url: str, filter: bool = True) -> [TorrentInfo]:
        soup = self.get_xml(_url)
        torrent_titles = [item.title.string for item in soup.find_all("item")]
        torrent_urls = [item.get("url") for item in soup.find_all("enclosure")]
        torrents = []
        for _title, torrent_url in zip(torrent_titles, torrent_urls):
            if filter:
                if re.search(FILTER, _title) is None:
                    torrents.append(TorrentInfo(_title, torrent_url))
            else:
                torrents.append(TorrentInfo(_title, torrent_url))
        return torrents

    def get_torrent(self, _url) -> TorrentInfo:
        soup = self.get_xml(_url)
        item = soup.find("item")
        enclosure = item.find("enclosure")
        return TorrentInfo(item.title.string, enclosure["url"])

    def get_xml(self, _url):
        return BeautifulSoup(self.get_url(_url).text, "xml")

    # API JSON
    def get_json(self, _url) -> dict:
        return self.get_url(_url).json()

    def post_json(self, _url, data: dict) -> dict:
        return self.post_url(_url, data).json()

    def post_data(self, _url, data: dict) -> dict:
        return self.post_url(_url, data)

    def get_html(self, _url):
        return self.get_url(_url).text

    def get_content(self, _url):
        return self.get_url(_url).content
