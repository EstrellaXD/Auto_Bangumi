import json
import logging
from typing import TypeAlias

from module.models import Bangumi, RSSItem, Torrent
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

# Cache for TMDB poster lookups by official_title
_poster_cache: dict[str, str | None] = {}


class SearchTorrent(RequestContent, RSSAnalyser):
    async def search_torrents(self, rss_item: RSSItem) -> list[Torrent]:
        return await self.get_torrents(rss_item.url)

    async def _fetch_tmdb_poster(self, title: str) -> str | None:
        """Fetch poster from TMDB if not in cache."""
        if title in _poster_cache:
            return _poster_cache[title]

        try:
            tmdb_info = await tmdb_parser(title, "zh", test=True)
            if tmdb_info and tmdb_info.poster_link:
                _poster_cache[title] = tmdb_info.poster_link
                return tmdb_info.poster_link
        except Exception as e:
            logger.debug(f"[Searcher] Failed to fetch TMDB poster for {title}: {e}")

        _poster_cache[title] = None
        return None

    async def analyse_keyword(
        self, keywords: list[str], site: str = "mikan", limit: int = 100
    ):
        rss_item = search_url(site, keywords)
        torrents = await self.search_torrents(rss_item)
        # yield for EventSourceResponse (Server Send)
        exist_list = []
        for torrent in torrents:
            if len(exist_list) >= limit:
                break
            bangumi = await self.torrent_to_data(torrent=torrent, rss=rss_item)
            if bangumi:
                special_link = self.special_url(bangumi, site).url
                if special_link not in exist_list:
                    bangumi.rss_link = special_link
                    exist_list.append(special_link)
                    # Fetch poster from TMDB if missing
                    if not bangumi.poster_link and bangumi.official_title:
                        tmdb_poster = await self._fetch_tmdb_poster(bangumi.official_title)
                        if tmdb_poster:
                            bangumi.poster_link = tmdb_poster
                    yield json.dumps(bangumi.dict(), separators=(",", ":"))

    @staticmethod
    def special_url(data: Bangumi, site: str) -> RSSItem:
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        url = search_url(site, keywords)
        return url

    async def search_season(self, data: Bangumi, site: str = "mikan") -> list[Torrent]:
        rss_item = self.special_url(data, site)
        torrents = await self.search_torrents(rss_item)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]
