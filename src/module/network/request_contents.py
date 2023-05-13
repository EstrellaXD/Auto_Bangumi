import re
import xml.etree.ElementTree
from dataclasses import dataclass
from bs4 import BeautifulSoup

from .request_url import RequestURL
from module.conf import settings


@dataclass
class TorrentInfo:
    name: str
    torrent_link: str
    homepage: str = None


class RequestContent(RequestURL):
    # Mikanani RSS
    def get_torrents(
            self,
            _url: str,
            _filter: str = "|".join(settings.rss_parser.filter)
    ) -> [TorrentInfo]:
        soup = self.get_xml(_url)
        torrent_titles = []
        torrent_urls = []
        torrent_homepage = []

        for item in soup.findall("./channel/item"):
            torrent_titles.append(item.find("title").text)
            torrent_urls.append(item.find("enclosure").attrib["url"])
            torrent_homepage.append(item.find("link").text)

        torrents = []
        for _title, torrent_url, homepage in zip(torrent_titles, torrent_urls, torrent_homepage):
            if re.search(_filter, _title) is None:
                torrents.append(TorrentInfo(_title, torrent_url, homepage))
        return torrents

    def get_mikan_info(self, _url) -> tuple[str, str]:
        content = self.get_html(_url)
        soup = BeautifulSoup(content, "html.parser")
        poster_div = soup.find("div", {"class": "bangumi-poster"})
        poster_style = poster_div.get("style")
        official_title = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]').text
        if poster_style:
            poster_path = poster_style.split("url('")[1].split("')")[0]
            return poster_path, official_title
        return "", ""

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

    def check_connection(self, _url=settings.downloader.host):
        return self.check_url(_url)
