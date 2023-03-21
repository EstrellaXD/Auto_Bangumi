from dataclasses import dataclass

from bs4 import BeautifulSoup

from .request_url import RequestURL

from module.conf import settings

import re


@dataclass
class TorrentInfo:
    name: str
    torrent_link: str


class RequestContent(RequestURL):
    # Mikanani RSS
    def get_torrents(self, _url: str) -> [TorrentInfo]:
        soup = self.get_xml(_url)
        torrent_titles = [item.title.string for item in soup.find_all("item")]
        torrent_urls = [item.get("url") for item in soup.find_all("enclosure")]
        torrents = []
        is_collection = 0

        user_reg = "|".join(settings.rss_parser.filter)
        # Priority download anime collection will cover user regular expressions
        if settings.bangumi_manage.eps_collection:
            # Remove the regular judgment about the anime collection
            user_reg = user_reg.replace('\\d+-\\d+', '').replace('||', '|').strip('|')

        for _title, torrent_url in zip(torrent_titles, torrent_urls):
            if not re.search(user_reg, _title):
                # Existence collection
                if re.search(r'\d+-\d+', _title):
                    # Clear
                    if not is_collection:
                        torrents = []
                        is_collection = 1
                    torrents.append(TorrentInfo(_title, torrent_url))
                if not is_collection:
                    torrents.append(TorrentInfo(_title, torrent_url))
        return torrents

    def get_torrent(self, _url) -> TorrentInfo:
        soup = self.get_xml(_url)
        item = soup.find("item")
        enclosure = item.find("enclosure")
        return TorrentInfo(item.title.string, enclosure["url"])

    def get_xml(self, url):
        return BeautifulSoup(self.get_url(url).text, "xml")

    # API JSON
    def get_json(self, _url) -> dict:
        return self.get_url(_url).json()
