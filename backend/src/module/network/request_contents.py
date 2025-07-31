import logging
import time
import xml.etree.ElementTree
from typing import Any

from httpx import Response

from module.models import Torrent

from .request_url import RequestURL
from .site import rss_parser
from module.utils import get_hash, torrent_to_link

logger = logging.getLogger(__name__)

_cache = {}
_max_cache_size = 1000

class RequestContent(RequestURL):

    def __init__(self):
        super().__init__()
    
    def _check_cache(self, url: str):
        if url in _cache:
            data, timestamp = _cache[url]['data'], _cache[url]['timestamp']
            if time.time() - timestamp < 60:  # 未过期
                return data
            else:
                del _cache[url]  # 过期就删除
        return None
    
    def _save_cache(self, url: str, data):
        if len(_cache) >= _max_cache_size:
            # 批量清理所有过期的缓存
            current_time = time.time()
            expired_keys = [
                key for key, value in _cache.items() 
                if current_time - value['timestamp'] > 60
            ]
            for key in expired_keys:
                del _cache[key]
            
            # 如果清理后还是达到上限，删除最老的一条
            if len(_cache) >= _max_cache_size:
                first_key = next(iter(_cache))
                del _cache[first_key]
        
        _cache[url] = {
            'data': data,
            'timestamp': time.time()
        }
    # 对错误包裹, 所有网络的错误到这里就结束了
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
        self, _url: str, retry: int = 3
    ) -> xml.etree.ElementTree.Element | None:
        # 检查缓存
        cached = self._check_cache(_url)
        if cached is not None:
            return cached
        
        try:
            req = await self.get_url(_url, retry)
            if req:
                result = xml.etree.ElementTree.fromstring(req.text)
                self._save_cache(_url, result)
                return result
        except xml.etree.ElementTree.ParseError:
            logger.warning(
                f"[Network] Cannot parser {_url}, please check the url is right"
            )
        except Exception as e:
            logger.error(f"[Network] Cannot get xml from {_url}: {e}")
        return None

    # API JSON
    async def get_json(self, _url: str) -> dict[str, Any]:
        # 检查缓存
        cached = self._check_cache(_url)
        if cached is not None:
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

    async def post_data(
        self, _url: str, data: dict[str, str], files: dict[str, bytes]|None=None
    ) -> Response:
        try:
            req = await self.post_url(_url, data, files)
            return req
        except Exception as e:
            logger.error(f"[Network] Cannot post data to {_url}: {e}")
        return Response(status_code=400)

    async def get_html(self, _url: str) -> str:
        # 检查缓存
        cached = self._check_cache(_url)
        if cached is not None:
            return cached
        
        try:
            req = await self.get_url(_url)
            if req:
                result = req.text
                self._save_cache(_url, result)
                return result
        except Exception as e:
            logger.error(f"[Network] Cannot get html from {_url}: {e}")
        return ""

    async def get_content(self, _url: str) -> bytes:
        # 检查缓存
        cached = self._check_cache(_url)
        if cached is not None:
            return cached
        
        try:
            req = await self.get_url(_url)
            if req:
                result = req.content
                self._save_cache(_url, result)
                return result
        except Exception as e:
            logger.error(f"[Network] Cannot get content from {_url}: {e}")
        return b""

    async def check_connection(self, _url: str) -> bool:
        return await self.check_url(_url)

    async def get_rss_title(self, _url: str) -> str | None:
        # 有一说一,不该在这里,放在 rss_parser 里面
        soup = await self.get_xml(_url)
        if soup:
            title = soup.find("./channel/title")
            logger.debug(
                f"XML structure: {xml.etree.ElementTree.tostring(title, encoding='unicode')}"
            )
            if title is not None:
                return title.text

    async def get_torrent_hash(self, _url: str) -> str:
        # 下载种子文件,处理 hash 与 url 不一致的情况
        if torrent_file := await self.get_content( _url):
            torrent_url = await torrent_to_link(torrent_file)
            torrent_hash = get_hash(torrent_url)
            return torrent_hash
        return ""


