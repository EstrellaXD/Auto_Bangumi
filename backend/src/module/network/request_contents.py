import logging
import time
import xml.etree.ElementTree
from typing import Any

import httpx
from httpx import Response

from module.exceptions import XMLParseError
from models import Torrent
from module.utils import get_torrent_hashes, process_title

from .request_url import RequestURL
from .site import rss_parser

logger = logging.getLogger(__name__)

_cache = {}
_max_cache_size = 1000


class RequestContent(RequestURL):
    def __init__(self):
        super().__init__()

    def _check_cache(self, url: str):
        if url in _cache:
            data, timestamp = _cache[url]["data"], _cache[url]["timestamp"]
            if time.time() - timestamp < 60:  # 未过期
                return data
            del _cache[url]  # 过期就删除
        return None

    def _save_cache(self, url: str, data):
        if len(_cache) >= _max_cache_size:
            # 批量清理所有过期的缓存
            current_time = time.time()
            expired_keys = [key for key, value in _cache.items() if current_time - value["timestamp"] > 60]
            for key in expired_keys:
                del _cache[key]

            # 如果清理后还是达到上限，删除最老的一条
            if len(_cache) >= _max_cache_size:
                first_key = next(iter(_cache))
                del _cache[first_key]

        _cache[url] = {"data": data, "timestamp": time.time()}

    async def get_torrents(
        self,
        _url: str,
        limit: int = 0,
        retry: int = 3,
    ) -> list[Torrent]:
        try:
            feeds = await self.get_xml(_url, retry)
            torrent_titles, torrent_urls, torrent_homepage = rss_parser(feeds)
            torrents: list[Torrent] = []
            for _title, torrent_url, homepage in zip(torrent_titles, torrent_urls, torrent_homepage):
                _title = process_title(_title)
                torrents.append(Torrent(name=_title, url=torrent_url, homepage=homepage))
            return torrents if limit == 0 else torrents[:limit]
        except Exception:
            raise

    async def get_xml(self, _url: str, retry: int = 3) -> xml.etree.ElementTree.Element:
        if cached := self._check_cache(_url):
            return cached
        try:
            req = await self.get_url(_url, retry)
            result = xml.etree.ElementTree.fromstring(req.text)
            self._save_cache(_url, result)
            return result
        except xml.etree.ElementTree.ParseError:
            raise XMLParseError(url=_url)
        except httpx.RequestError as e:
            logger.error(f"[Network] Cannot get xml from {_url}: {e}")
            raise

    # API JSON
    async def get_json(self, _url: str) -> dict[str, Any]:
        if cached := self._check_cache(_url):
            return cached
        try:
            req = await self.get_url(_url)
            if req:
                result = req.json()
                self._save_cache(_url, result)
                return result
        except Exception as e:
            logger.error(f"[Network] Cannot get json from {_url}: {e}")
        return {}

    async def post_data(self, _url: str, data: dict[str, str], files: dict[str, bytes] | None = None) -> Response:
        req = await self.post_url(_url, data, files)
        return req

    async def get_html(self, _url: str) -> str:
        if cached := self._check_cache(_url):
            return cached
        req = await self.get_url(_url)
        result = req.text
        self._save_cache(_url, result)
        return result

    async def get_content(self, _url: str) -> bytes:
        if cached := self._check_cache(_url):
            return cached
        try:
            req = await self.get_url(_url)
            result = req.content
            self._save_cache(_url, result)
            return result
        except httpx.RequestError as e:
            logger.error(f"[Network] Cannot get content from {_url}: {e}")
            raise

    async def get_rss_title(self, _url: str) -> str | None:
        # 有一说一,不该在这里,放在 rss_parser 里面
        try:
            soup = await self.get_xml(_url)
            title = soup.find("./channel/title")
            if title is not None:
                return title.text
        except Exception as e:
            logger.error(f"[Network] Cannot get rss title from {_url}: {e}")
        return None

    async def get_torrent_hash(self, _url: str) -> tuple[bytes,list[str]]:
        # 下载种子文件,处理 hash 与 url 不一致的情况
        torrent_file = await self.get_content(_url)
        torrent_hash = get_torrent_hashes(torrent_file)
        return torrent_file,torrent_hash
