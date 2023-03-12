from dataclasses import dataclass

from .request_url import RequestURL
from module.conf import settings

import re

FILTER = "|".join(settings.rss_parser.filter)


@dataclass
class TorrentInfo:
    name: str
    torrent_link: str


class RequestContent(RequestURL):
    # Mikanani RSS
    def get_torrents(self, _url: str) -> [TorrentInfo]:
        soup = self.session.get_content(_url)
        torrent_titles = [item.title.string for item in soup.find_all("item")]
        torrent_urls = [item.get("url") for item in soup.find_all("enclosure")]
        torrents = []
        for _title, torrent_url in zip(torrent_titles, torrent_urls):
            if re.search(FILTER, _title) is None:
                torrents.append(TorrentInfo(_title, torrent_url))
        return torrents

    def get_torrent(self, _url) -> TorrentInfo:
        soup = self.session.get_content(_url)
        item = soup.find("item")
        enclosure = item.find("enclosure")
        return TorrentInfo(item.title.string, enclosure["url"])

    # API JSON
    def get_json(self, _url) -> dict:
        return self.session.get_content(_url, content="json")
