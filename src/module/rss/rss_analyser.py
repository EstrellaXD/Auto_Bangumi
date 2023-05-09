import logging

from module.network import RequestContent
from module.parser import TitleParser
from module.models import Config, BangumiData
from module.database import DataOperator
from module.conf import settings

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self):
        self._title_analyser = TitleParser()

    def rss_to_data(self, rss_link: str, full_parse: bool = True) -> list[BangumiData]:
        with RequestContent() as req:
            rss_torrents = req.get_torrents(rss_link)
        title_dict = {torrent.name: torrent.homepage for torrent in rss_torrents}
        with DataOperator() as op:
            new_dict = op.match_list(title_dict, rss_link)
            if not new_dict:
                logger.debug("No new title found.")
                return []
            _id = op.gen_id()
            new_data = []
            # New List
            with RequestContent() as req:
                for raw_title, homepage in new_dict.items():
                    data = self._title_analyser.raw_parser(
                        raw=raw_title, rss_link=rss_link, _id=_id
                    )
                    if data and data.title_raw not in [i.title_raw for i in new_data]:
                        poster_link, official_title = req.get_mikan_info(homepage)
                        data.poster_link = poster_link
                        # Official title type
                        if settings.rss_parser.parser_type == "mikan":
                            data.official_title = official_title
                        elif settings.rss_parser.parser_type == "tmdb":
                            official_title, season, year = self._title_analyser.tmdb_parser(
                                data.official_title,
                                data.season,
                                settings.rss_parser.language
                            )
                            data.official_title = official_title
                            data.year = year
                            data.season = season
                        else:
                            pass
                        if not full_parse:
                            op.insert(data)
                            return [data]
                        new_data.append(data)
                        _id += 1
                        logger.debug(f"New title found: {data.official_title}")
                op.insert_list(new_data)
            return new_data

    def run(self, rss_link: str):
        logger.info("Start collecting RSS info.")
        try:
            self.rss_to_data(rss_link)
        except Exception as e:
            logger.debug(e)


if __name__ == '__main__':
    from module.conf import setup_logger
    setup_logger()
    link = "https://mikanani.me/RSS/Bangumi?bangumiId=2906&subgroupid=552"
    data = RSSAnalyser().rss_to_data(link)
