import asyncio
import logging
import re

from module.conf import settings
from module.database import Database, engine
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent
from module.parser import MikanParser, RawParser, TmdbParser

logger = logging.getLogger(__name__)


class RSSAnalyser():
    def __init__(self,_engine=engine) -> None:
        self.engine = _engine

    async def official_title_parser(self, bangumi: Bangumi, rss: RSSItem, torrent: Torrent):
        if rss.parser == "mikan":
            try:
                parsered_bangumi = await  MikanParser().parser(torrent.homepage) 
                bangumi.poster_link, bangumi.official_title =  parsered_bangumi.poster_link,parsered_bangumi.official_title
            except AttributeError:
                logger.warning("[Parser] Mikan torrent has no homepage info.")
                pass
        elif rss.parser == "tmdb":
            parsered_bangumi = await TmdbParser.parser(
                bangumi.official_title, bangumi.season, settings.rss_parser.language
            )
            bangumi.official_title = parsered_bangumi.official_title
            bangumi.year = parsered_bangumi.year
            bangumi.season = parsered_bangumi.season
            bangumi.poster_link = parsered_bangumi.poster_link
        else:
            pass
        bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)

    @staticmethod
    async def get_rss_torrents(rss_link: str, full_parse: bool = True) -> list[Torrent]:
        async with RequestContent() as req:
            _fileter = "" if full_parse else r"\d+-\d+"
            rss_torrents = await req.get_torrents(rss_link, _filter=_fileter)
        return rss_torrents

    async def torrents_to_data(
        self, torrents: list[Torrent], rss: RSSItem, full_parse: bool = True
    ) -> list[Bangumi]:
        """
        return new bangumi list
        """
        new_data = []
        tasks = []
        for torrent in torrents:
            bangumi = RawParser().parser(raw=torrent.name)
            if bangumi and bangumi.title_raw not in [_.title_raw for _ in new_data]:
                tasks.append(self.official_title_parser(bangumi=bangumi, rss=rss, torrent=torrent))
                bangumi.rss_link = rss.url
                new_data.append(bangumi)
                logger.info(f"[RSS] New bangumi founded: {bangumi.official_title}")
                if not full_parse:
                    break
        await asyncio.gather(*tasks)
        return new_data

    async def torrent_to_data(self, torrent: Torrent, rss: RSSItem) -> Bangumi|None:
        bangumi = RawParser().parser(raw=torrent.name)
        if bangumi:
            await self.official_title_parser(bangumi=bangumi, rss=rss, torrent=torrent)
            bangumi.rss_link = rss.url
            return bangumi

    async def rss_to_data(
        self, rss: RSSItem, full_parse: bool = True
    ) -> list[Torrent]:
        """
        full parse
        find new bangumi from rss link and add new bangumi to database
        return new bangumi list
        """
        rss_torrents = await self.get_rss_torrents(rss.url, full_parse)
        with Database(self.engine) as database:
            torrents_to_add = database.bangumi.match_list(rss_torrents, rss.url,aggrated=rss.aggregate)

            if not torrents_to_add:
                logger.debug("[RSS] No new title has been found.")
                return []
            # New List
            new_data = await self.torrents_to_data(torrents_to_add, rss, full_parse)
            if new_data:
                # Add to database
                database.bangumi.add_all(new_data)
                return rss_torrents
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
