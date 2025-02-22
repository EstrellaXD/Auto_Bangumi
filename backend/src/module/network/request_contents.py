import logging
import xml.etree.ElementTree
from typing import Any

from httpx import Response

from module.models import Torrent

from .request_url import RequestURL
from .site import rss_parser

logger = logging.getLogger(__name__)


class RequestContent(RequestURL):
    async def get_torrents(
        self,
        _url: str,
        limit: int = 0,
        retry: int = 3,
    ) -> list[Torrent]:
        feeds = await self.get_xml(_url, retry)
        if feeds:
            torrent_titles, torrent_urls, torrent_homepage = rss_parser(feeds)
            torrents: list[Torrent] = []
            for _title, torrent_url, homepage in zip(
                torrent_titles, torrent_urls, torrent_homepage
            ):
                torrents.append(
                    Torrent(name=_title, url=torrent_url, homepage=homepage)
                )
            return torrents if limit == 0 else torrents[:limit]
        else:
            logger.error(f"[Network] Torrents list is empty: {_url}")
            return []

    async def get_xml(
        self, _url, retry: int = 3
    ) -> xml.etree.ElementTree.Element | None:
        req = await self.get_url(_url, retry)
        if req:
            try:
                return xml.etree.ElementTree.fromstring(req.text)
            except xml.etree.ElementTree.ParseError:
                logging.warning(
                    f"[Network] Cannot parser {_url}, please check the url is right"
                )
                return None

    # API JSON
    async def get_json(self, _url) -> dict[str, Any]:
        req = await self.get_url(_url)
        if req:
            return req.json()
        else:
            return {}

    async def post_data(
        self, _url, data: dict[str, str], files: dict[str, bytes]
    ) -> Response | None:
        req = await self.post_url(_url, data, files)

        return req
        # if req:
        #     return req.json()
        # else:
        #     return {}

    async def get_html(self, _url):
        req = await self.get_url(_url)
        if req:
            return req.text

    async def get_content(self, _url):
        req = await self.get_url(_url)
        if req:
            return req.content

    async def check_connection(self, _url):
        return await self.check_url(_url)

    async def get_rss_title(self, _url):
        # 有一说一,不该在这里,放在 rss_parser 里面
        soup = await self.get_xml(_url)
        if soup:
            if soup := soup.find("./channel/title"):
                return soup.text
