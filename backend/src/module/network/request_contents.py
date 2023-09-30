import re
import logging
import xml.etree.ElementTree

from module.conf import settings
from module.models import Torrent

from .request_url import RequestURL
from .site import rss_parser

logger = logging.getLogger(__name__)


class RequestContent(RequestURL):
    def get_torrents(
        self,
        _url: str,
        _filter: str = "|".join(settings.rss_parser.filter),
        limit: int = None,
        retry: int = 3,
    ) -> list[Torrent]:
        soup = self.get_xml(_url, retry)
        if soup:
            torrent_titles, torrent_urls, torrent_homepage = rss_parser(soup)
            torrents: list[Torrent] = []
            for _title, torrent_url, homepage in zip(
                torrent_titles, torrent_urls, torrent_homepage
            ):
                if re.search(_filter, _title) is None:
                    torrents.append(
                        Torrent(name=_title, url=torrent_url, homepage=homepage)
                    )
                if isinstance(limit, int):
                    if len(torrents) >= limit:
                        break
            return torrents
        else:
            logger.warning(f"[Network] Failed to get torrents: {_url}")
            return []

    def get_xml(self, _url, retry: int = 3) -> xml.etree.ElementTree.Element:
        req = self.get_url(_url, retry)
        if req:
            return xml.etree.ElementTree.fromstring(req.text)

    # API JSON
    def get_json(self, _url) -> dict:
        req = self.get_url(_url)
        if req:
            return req.json()

    def post_json(self, _url, data: dict) -> dict:
        return self.post_url(_url, data).json()

    def post_data(self, _url, data: dict) -> dict:
        return self.post_url(_url, data)

    def get_html(self, _url):
        return self.get_url(_url).text

    def get_content(self, _url):
        req = self.get_url(_url)
        if req:
            return req.content

    def check_connection(self, _url):
        return self.check_url(_url)

    def get_rss_title(self, _url):
        soup = self.get_xml(_url)
        if soup:
            return soup.find("./channel/title").text
