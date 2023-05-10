import logging

from module.network import RequestContent
from module.parser import TitleParser
from module.models import BangumiData
from module.database import BangumiDatabase
from module.conf import settings

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self):
        self._title_analyser = TitleParser()

    def official_title_parser(self, data: BangumiData, mikan_title: str):
        if settings.rss_parser.parser_type == "mikan":
            data.official_title = mikan_title
        elif settings.rss_parser.parser_type == "tmdb":
            tmdb_title, season, year = self._title_analyser.tmdb_parser(
                data.official_title,
                data.season,
                settings.rss_parser.language
            )
            data.official_title = tmdb_title
            data.year = year
            data.season = season
        else:
            pass

    @staticmethod
    def get_rss_torrents(rss_link: str, full_parse: bool = True) -> list:
        with RequestContent() as req:
            if full_parse:
                rss_torrents = req.get_torrents(rss_link)
            else:
                rss_torrents = req.get_torrents(rss_link, "\\d+-\\d+")
        return rss_torrents

    def get_new_data_list(self, new_dict: dict, rss_link: str, _id: int, full_parse: bool = True) -> list:
        new_data = []
        with RequestContent() as req:
            for raw_title, homepage in new_dict.items():
                data = self._title_analyser.raw_parser(
                    raw=raw_title, rss_link=rss_link, _id=_id
                )
                if data and data.title_raw not in [i.title_raw for i in new_data]:
                    poster_link, mikan_title = req.get_mikan_info(homepage)
                    data.poster_link = poster_link
                    self.official_title_parser(data, mikan_title)
                    if not full_parse:
                        return [data]
                    new_data.append(data)
                    _id += 1
                    logger.debug(f"New title found: {data.official_title}")
        return new_data

    def rss_to_data(self, rss_link: str, full_parse: bool = True) -> list[BangumiData]:
        rss_torrents = self.get_rss_torrents(rss_link, full_parse)
        title_dict = {torrent.name: torrent.homepage for torrent in rss_torrents}
        with BangumiDatabase() as database:
            new_dict = database.match_list(title_dict, rss_link)
            if not new_dict:
                logger.debug("No new title found.")
                return []
            _id = database.gen_id()
            # New List
            new_data = self.get_new_data_list(new_dict, rss_link, _id, full_parse)
            database.insert_list(new_data)
        return new_data

    def run(self, rss_link: str):
        logger.info("Start collecting RSS info.")
        try:
            self.rss_to_data(rss_link)
        except Exception as e:
            logger.debug(e)
            logger.error("Failed to collect RSS info.")
