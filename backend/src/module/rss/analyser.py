import logging
import re

from module.conf import settings
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent
from module.parser import TitleParser

from .engine import RSSEngine

logger = logging.getLogger(__name__)


class RSSAnalyser:
    async def official_title_parser(
        self,
        bangumi: Bangumi,
        rss: RSSItem,
        torrent: Torrent,
        fetch_poster: bool = True,
    ):
        if not fetch_poster:
            pass
        elif rss.parser == "mikan":
            if not torrent.homepage:
                logger.warning("Mikan torrent has no homepage info.")
            else:
                try:
                    poster_link, official_title = await TitleParser.mikan_parser(
                        torrent.homepage
                    )
                except AttributeError as e:
                    logger.warning(
                        f"Failed to parse Mikan homepage " f"{torrent.homepage}: {e}"
                    )
                else:
                    bangumi.poster_link = poster_link
                    if official_title:
                        bangumi.official_title = official_title
        elif rss.parser == "tmdb":
            rss_name = (rss.name or "").strip()
            query_title = (
                rss_name
                if rss_name and not rss.aggregate
                else bangumi.official_title
            )
            tmdb_title, season, year, poster_link = await TitleParser.tmdb_parser(
                query_title,
                bangumi.season,
                settings.rss_parser.language,
                episode_type=bangumi.episode_type,
            )
            bangumi.official_title = tmdb_title
            bangumi.year = year
            bangumi.season = season
            bangumi.poster_link = poster_link
        else:
            pass
        if bangumi.official_title:
            bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)

    @staticmethod
    async def get_rss_torrents(rss_link: str, full_parse: bool = True) -> list[Torrent]:
        async with RequestContent() as req:
            if full_parse:
                rss_torrents = await req.get_torrents(rss_link)
            else:
                rss_torrents = await req.get_torrents(rss_link, "\\d+-\\d+")
        return rss_torrents

    async def torrents_to_data(
        self, torrents: list[Torrent], rss: RSSItem, full_parse: bool = True
    ) -> list:
        new_data = []
        seen_titles: set[str] = set()
        for torrent in torrents:
            bangumi = await TitleParser.raw_parser(raw=torrent.name)
            if bangumi and bangumi.title_raw not in seen_titles:
                await self.official_title_parser(
                    bangumi=bangumi, rss=rss, torrent=torrent
                )
                bangumi.rss_link = rss.url
                if not full_parse:
                    return [bangumi]
                seen_titles.add(bangumi.title_raw)
                new_data.append(bangumi)
                logger.info(f"New bangumi founded: {bangumi.official_title}")
        return new_data

    async def torrent_to_data(
        self, torrent: Torrent, rss: RSSItem, fetch_poster: bool = True
    ) -> Bangumi | None:
        bangumi = await TitleParser.raw_parser(raw=torrent.name)
        if bangumi:
            await self.official_title_parser(
                bangumi=bangumi, rss=rss, torrent=torrent, fetch_poster=fetch_poster
            )
            bangumi.rss_link = rss.url
            return bangumi
        return None

    async def rss_to_data(
        self, rss: RSSItem, engine: RSSEngine, full_parse: bool = True
    ) -> list[Bangumi]:
        rss_torrents = await self.get_rss_torrents(rss.url, full_parse)
        torrents_to_add = await engine.db.bangumi.match_list(rss_torrents, rss.url)
        if not torrents_to_add:
            logger.debug("No new title has been found.")
            return []
        # New List
        new_data = await self.torrents_to_data(torrents_to_add, rss, full_parse)
        if new_data:
            # Add to database
            await engine.db.bangumi.add_all(new_data)
            return new_data
        else:
            return []

    async def link_to_data(self, rss: RSSItem) -> Bangumi | ResponseModel:
        torrents = await self.get_rss_torrents(rss.url, False)
        if not torrents:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en="Cannot find any torrent.",
                msg_zh="无法找到种子。",
            )
        for torrent in torrents:
            data = await self.torrent_to_data(torrent, rss)
            if data:
                return data
        return ResponseModel(
            status=False,
            status_code=406,
            msg_en="Cannot parse this link.",
            msg_zh="无法解析此链接。",
        )
