import re
import logging
import xml.etree.ElementTree

from module.conf import settings
from module.models import Torrent

from .request_url import RequestURL
from .site import mikan_parser

logger = logging.getLogger(__name__)


class RequestContent(RequestURL):
    def get_torrents(
        self,
        _url: str,
        _filter: str = "|".join(settings.rss_parser.filter),
        limit: int = 100,
        retry: int = 3,
    ) -> list[Torrent]:
        try:
            soup = self.get_xml(_url, retry)
            torrent_titles, torrent_urls, torrent_homepage = mikan_parser(soup)
            torrents: list[Torrent] = []
            for _title, torrent_url, homepage in zip(
                torrent_titles, torrent_urls, torrent_homepage
            ):
                if re.search(_filter, _title) is None:
                    torrents.append(
                        Torrent(name=_title, url=torrent_url, homepage=homepage)
                    )
                if len(torrents) >= limit:
                    break
            return torrents
        except ConnectionError:
            return []

    def get_xml(self, _url, retry: int = 3) -> xml.etree.ElementTree.Element:
        return xml.etree.ElementTree.fromstring(self.get_url(_url, retry).text)

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

    def check_connection(self, _url):
        return self.check_url(_url)

    def get_rss_title(self, _url):
        try:
            soup = self.get_xml(_url)
            return soup.find("./channel/title").text
        except ConnectionError:
            logger.warning(f"Failed to get RSS title: {_url}")
