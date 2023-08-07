import logging
import re

from .engine import RSSEngine

from module.conf import settings
from module.models import Bangumi, Torrent
from module.network import RequestContent
from module.parser import TitleParser

logger = logging.getLogger(__name__)


class RSSAnalyser(TitleParser):
    def official_title_parser(self, data: Bangumi, mikan_title: str):
        if settings.rss_parser.parser_type == "mikan":
            data.official_title = mikan_title if mikan_title else data.official_title
        elif settings.rss_parser.parser_type == "tmdb":
            tmdb_title, season, year = self.tmdb_parser(
                data.official_title, data.season, settings.rss_parser.language
            )
            data.official_title = tmdb_title
            data.year = year
            data.season = season
        else:
            pass
        data.official_title = re.sub(r"[/:.\\]", " ", data.official_title)

    @staticmethod
    def get_rss_torrents(rss_link: str, full_parse: bool = True) -> list[Torrent]:
        with RequestContent() as req:
            if full_parse:
                rss_torrents = req.get_torrents(rss_link)
            else:
                rss_torrents = req.get_torrents(rss_link, "\\d+-\\d+")
        return rss_torrents

    def torrents_to_data(
        self, torrents: list, rss_link: str, full_parse: bool = True
    ) -> list:
        new_data = []
        for torrent in torrents:
            data = self.raw_parser(raw=torrent.name)
            if data and data.title_raw not in [i.title_raw for i in new_data]:
                with RequestContent() as req:
                    poster_link, mikan_title = req.get_mikan_info(torrent.homepage)
                data.poster_link = poster_link
                data.rss_link = rss_link
                self.official_title_parser(data, mikan_title)
                if not full_parse:
                    return [data]
                new_data.append(data)
                logger.debug(f"[RSS] New title found: {data.official_title}")
        return new_data

    def torrent_to_data(self, torrent: Torrent) -> Bangumi:
        data = self.raw_parser(raw=torrent.name)
        if data:
            with RequestContent() as req:
                poster_link, mikan_title = req.get_mikan_info(torrent.homepage)
            data.poster_link = poster_link
            self.official_title_parser(data, mikan_title)
            return data

    def rss_to_data(
        self, rss_link: str, engine: RSSEngine, full_parse: bool = True
    ) -> list[Bangumi]:
        rss_torrents = self.get_rss_torrents(rss_link, full_parse)
        torrents_to_add = engine.bangumi.match_list(rss_torrents, rss_link)
        if not torrents_to_add:
            logger.debug("[RSS] No new title has been found.")
            return []
        # New List
        new_data = self.torrents_to_data(torrents_to_add, rss_link, full_parse)
        if new_data:
            # Add to database
            engine.bangumi.add_all(new_data)
            return new_data
        else:
            return []

    def link_to_data(self, link: str) -> Bangumi:
        torrents = self.get_rss_torrents(link, False)
        for torrent in torrents:
            data = self.torrent_to_data(torrent)
            if data:
                return data
