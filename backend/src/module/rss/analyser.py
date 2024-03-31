import logging
import re

from module.conf import settings
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent
from module.parser import TitleParser

from .engine import RSSEngine

logger = logging.getLogger(__name__)


class RSSAnalyser(TitleParser):
    def official_title_parser(self, bangumi: Bangumi, rss: RSSItem, torrent: Torrent):
        if rss.parser == "mikan":
            try:
                bangumi.poster_link, bangumi.official_title = self.mikan_parser(
                    torrent.homepage
                )
            except AttributeError:
                logger.warning("[Parser] Mikan torrent has no homepage info.")
                pass
        elif rss.parser == "tmdb":
            tmdb_title, season, year, poster_link = self.tmdb_parser(
                bangumi.official_title, bangumi.season, settings.rss_parser.language
            )
            bangumi.official_title = tmdb_title
            bangumi.year = year
            bangumi.season = season
            bangumi.poster_link = poster_link
        else:
            pass
        bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)

    @staticmethod
    def get_rss_torrents(rss_link: str, full_parse: bool = True) -> list[Torrent]:
        with RequestContent() as req:
            if full_parse:
                rss_torrents = req.get_torrents(rss_link)
            else:
                rss_torrents = req.get_torrents(rss_link, "\\d+-\\d+")
        return rss_torrents

    def torrents_to_data(
        self, torrents: list[Torrent], rss: RSSItem, full_parse: bool = True
    ) -> list:
        new_data = []
        for torrent in torrents:
            bangumi = self.raw_parser(raw=torrent.name)
            if bangumi and bangumi.title_raw not in [i.title_raw for i in new_data]:
                self.official_title_parser(bangumi=bangumi, rss=rss, torrent=torrent)
                if not full_parse:
                    return [bangumi]
                new_data.append(bangumi)
                logger.info(f"[RSS] New bangumi founded: {bangumi.official_title}")
        return new_data

    def torrent_to_data(self, torrent: Torrent, rss: RSSItem) -> Bangumi:
        bangumi = self.raw_parser(raw=torrent.name)
        if bangumi:
            self.official_title_parser(bangumi=bangumi, rss=rss, torrent=torrent)
            bangumi.rss_link = rss.url
            return bangumi

    def rss_to_data(
        self, rss: RSSItem, engine: RSSEngine, full_parse: bool = True
    ) -> list[Bangumi]:
        all_rss_torrents = self.get_rss_torrents(rss.url, full_parse)
        new_data = []
        for torrent in all_rss_torrents:
            bangumi = self.torrent_to_data(torrent, rss)
            q_bangumi = engine.bangumi.search_official_title(bangumi.official_title)
            if(not q_bangumi):
                new_data.append(bangumi)
        # New List
        if new_data:
            # Add to database
            engine.bangumi.add_all(new_data)
            return new_data
        else:
            return []

    def link_to_data(self, rss: RSSItem) -> Bangumi | ResponseModel:
        torrents = self.get_rss_torrents(rss.url, False)
        if not torrents:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en="Cannot find any torrent.",
                msg_zh="无法找到种子。",
            )
        for torrent in torrents:
            data = self.torrent_to_data(torrent, rss)
            if data:
                return data
        return ResponseModel(
            status=False,
            status_code=406,
            msg_en="Cannot parse this link.",
            msg_zh="无法解析此链接。",
        )

