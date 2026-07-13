import json
import logging
from collections import OrderedDict
from typing import TypeAlias

from module.conf import settings
from module.models import Bangumi, Movie, RSSItem, Torrent
from module.network import RequestContent
from module.parser.analyser.tmdb_parser import tmdb_parser
from module.rss import RSSAnalyser

from .provider import search_url

logger = logging.getLogger(__name__)

SEARCH_KEY = [
    "group_name",
    "title_raw",
    "season_raw",
    "subtitle",
    "source",
    "dpi",
]

BangumiJSON: TypeAlias = str

# Cache for TMDB preview lookups by official_title. Bounded (LRU-ish,
# oldest-evicted) like _tmdb_cache/_mikan_cache — was previously a plain dict
# and grew unbounded for the life of the process. Values are keyed by parser
# language because the title is localized while the poster URL usually is not.
_POSTER_CACHE_MAX = 512
_poster_cache: "OrderedDict[str, dict[str, tuple[str | None, str | None]]]" = (
    OrderedDict()
)


def reset_cache() -> None:
    """清空 TMDB 海报查询缓存。配置重载（如 tmdb_base_url 变更）后必须调用，
    否则会继续返回旧接口地址下缓存的结果。"""
    _poster_cache.clear()


class SearchTorrent:
    def __init__(self):
        self.analyser = RSSAnalyser()

    async def search_torrents(self, rss_item: RSSItem) -> list[Torrent]:
        async with RequestContent() as req:
            return await req.get_torrents(rss_item.url)

    async def _fetch_tmdb_preview(self, title: str) -> tuple[str | None, str | None]:
        """Fetch localized title and poster URL from TMDB for search previews."""
        language = settings.rss_parser.language
        if title in _poster_cache and language in _poster_cache[title]:
            _poster_cache.move_to_end(title)
            return _poster_cache[title][language]

        localized_title = None
        poster_link = None
        try:
            tmdb_info = await tmdb_parser(title, language, test=True)
            if tmdb_info:
                localized_title = tmdb_info.title
                poster_link = tmdb_info.poster_link
        except Exception as e:
            logger.debug("Failed to fetch TMDB preview for %s: %s", title, e)

        if title not in _poster_cache and len(_poster_cache) >= _POSTER_CACHE_MAX:
            _poster_cache.popitem(last=False)
        _poster_cache.setdefault(title, {})[language] = (localized_title, poster_link)
        return localized_title, poster_link

    async def _fetch_tmdb_poster(self, title: str) -> str | None:
        """Fetch poster from TMDB if not in cache."""
        _, poster_link = await self._fetch_tmdb_preview(title)
        return poster_link

    async def analyse_keyword(
        self, keywords: list[str], site: str = "mikan", limit: int = 100
    ):
        rss_item = search_url(site, keywords)
        torrents = await self.search_torrents(rss_item)
        # yield for EventSourceResponse (Server Send)
        exist_list: list[str] = []
        for torrent in torrents:
            if len(exist_list) >= limit:
                break
            # Skip the per-torrent Mikan homepage fetch / poster download here:
            # interactive search can return many results and doing that fetch
            # serially for each one makes the search feel unresponsive. Poster
            # is filled in afterwards from the (title-keyed, cached) TMDB lookup.
            bangumi = await self.analyser.torrent_to_data(
                torrent=torrent, rss=rss_item, fetch_poster=False
            )
            if bangumi:
                special_link = self.special_url(bangumi, site).url
                if special_link not in exist_list:
                    bangumi.rss_link = special_link
                    exist_list.append(special_link)
                    # Fetch localized title and poster URL from TMDB if available.
                    if bangumi.official_title:
                        tmdb_title, tmdb_poster = await self._fetch_tmdb_preview(
                            bangumi.official_title
                        )
                        if tmdb_title:
                            bangumi.official_title = tmdb_title
                        if not bangumi.poster_link and tmdb_poster:
                            bangumi.poster_link = tmdb_poster
                    yield json.dumps(bangumi.dict(), separators=(",", ":"))

    @staticmethod
    def special_url(data: Bangumi | Movie, site: str) -> RSSItem:
        keywords = [value for key in SEARCH_KEY if (value := getattr(data, key, None))]
        url = search_url(site, keywords)
        return url

    async def search_season(self, data: Bangumi, site: str = "mikan") -> list[Torrent]:
        rss_item = self.special_url(data, site)
        torrents = await self.search_torrents(rss_item)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]
