import re
import xml.etree.ElementTree
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
    def get_torrents(self, _url: str, _filter: bool = True) -> [TorrentInfo]:
        soup = self.get_xml(_url)
        torrent_titles = []
        torrent_urls = []
        torrent_homepage = []

        for item in soup.findall("./channel/item"):
            torrent_titles.append(item.find("title").text)
            torrent_urls.append(item.find("enclosure").attrib["url"])
            torrent_homepage.append(item.find("link").text)

        torrents = []
        for _title, torrent_url in zip(torrent_titles, torrent_urls):
            if _filter:
                if re.search(FILTER, _title) is None:
                    torrents.append(TorrentInfo(_title, torrent_url))
            else:
                torrents.append(TorrentInfo(_title, torrent_url))
        return torrents

    def get_poster(self, _url):
        content = self.get_html(_url).text
        soup = BeautifulSoup(content, "html.parser")
        div = soup.find("div", {"class": "bangumi-poster"})
        style = div.get("style")
        if style:
            return style.split("url('")[1].split("')")[0]
        return None

    def get_xml(self, _url) -> xml.etree.ElementTree.Element:
        return xml.etree.ElementTree.fromstring(self.get_url(_url).text)

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
