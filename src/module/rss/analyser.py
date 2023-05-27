import re
import logging

from module.network import RequestContent, TorrentInfo
from module.parser import TitleParser
from module.models import BangumiData
from module.database import BangumiDatabase
from module.conf import settings

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self):
        self._title_analyser = TitleParser()
        with BangumiDatabase() as db:
            db.update_table()

    def official_title_parser(self, data: BangumiData, mikan_title: str):
        if settings.rss_parser.parser_type == "mikan":
            data.official_title = mikan_title if mikan_title else data.official_title
        elif settings.rss_parser.parser_type == "tmdb":
            tmdb_title, season, year = self._title_analyser.tmdb_parser(
                data.official_title, data.season, settings.rss_parser.language
            )
            data.official_title = tmdb_title
            data.year = year
            data.season = season
        else:
            pass
        data.official_title = re.sub(r"[/:.\\]", " ", data.official_title)

    @staticmethod
    def get_rss_torrents(rss_link: str, full_parse: bool = True) -> list:
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
            data = self._title_analyser.raw_parser(raw=torrent.name, rss_link=rss_link)
            if data and data.title_raw not in [i.title_raw for i in new_data]:
                try:
                    poster_link, mikan_title = (
                        torrent.poster_link,
                        torrent.official_title,
                    )
                except AttributeError:
                    poster_link, mikan_title = None, None
                data.poster_link = poster_link
                self.official_title_parser(data, mikan_title)
                if not full_parse:
                    return [data]
                new_data.append(data)
                logger.debug(f"[RSS] New title found: {data.official_title}")
        return new_data

    def torrent_to_data(self, torrent: TorrentInfo, rss_link: str | None = None) -> BangumiData:
        data = self._title_analyser.raw_parser(raw=torrent.name, rss_link=rss_link)
        if data:
            try:
                poster_link, mikan_title = (
                    torrent.poster_link,
                    torrent.official_title,
                )
            except AttributeError:
                poster_link, mikan_title = None, None
            data.poster_link = poster_link
            self.official_title_parser(data, mikan_title)
            return data

    def rss_to_data(self, rss_link: str, full_parse: bool = True) -> list[BangumiData]:
        rss_torrents = self.get_rss_torrents(rss_link, full_parse)
        with BangumiDatabase() as database:
            torrents_to_add = database.match_list(rss_torrents, rss_link)
            if not torrents_to_add:
                logger.debug("[RSS] No new title has been found.")
                return []
            # New List
            new_data = self.torrents_to_data(torrents_to_add, rss_link, full_parse)
            if full_parse:
                database.insert_list(new_data)
        return new_data

    def run(self, rss_link: str = settings.rss_link):
        logger.info("[RSS] Start collecting RSS info.")
        try:
            self.rss_to_data(rss_link)
        except Exception as e:
            logger.debug(f"[RSS] {e}")
            logger.error("[RSS] Failed to collect RSS info.")
