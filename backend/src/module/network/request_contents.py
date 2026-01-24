import logging
import re
import xml.etree.ElementTree

from module.conf import settings
from module.models import Torrent

from .request_url import RequestURL
from .site import rss_parser

logger = logging.getLogger(__name__)


class RequestContent(RequestURL):
    async def get_torrents(
        self,
        _url: str,
        _filter: str = None,
        limit: int = None,
        retry: int = 3,
    ) -> list[Torrent]:
        soup = await self.get_xml(_url, retry)
        if soup:
            parsed_items = rss_parser(soup)
            torrents: list[Torrent] = []
            if _filter is None:
                _filter = "|".join(settings.rss_parser.filter)
            for _title, torrent_url, homepage in parsed_items:
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

    async def get_xml(self, _url, retry: int = 3) -> xml.etree.ElementTree.Element:
        req = await self.get_url(_url, retry)
        if req:
            return xml.etree.ElementTree.fromstring(req.text)

    # API JSON
    async def get_json(self, _url) -> dict:
        req = await self.get_url(_url)
        if req:
            return req.json()

    async def post_json(self, _url, data: dict) -> dict:
        resp = await self.post_url(_url, data)
        return resp.json()

    async def post_data(self, _url, data: dict):
        return await self.post_url(_url, data)

    async def post_files(self, _url, data: dict, files: dict):
        return await self.post_form(_url, data, files)

    async def get_html(self, _url):
        resp = await self.get_url(_url)
        return resp.text

    async def get_content(self, _url):
        req = await self.get_url(_url)
        if req:
            return req.content

    async def check_connection(self, _url):
        return await self.check_url(_url)

    async def get_rss_title(self, _url):
        soup = await self.get_xml(_url)
        if soup:
            return soup.find("./channel/title").text
