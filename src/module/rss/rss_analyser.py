import logging

from module.network import RequestContent
from module.parser import TitleParser
from module.models import Config, BangumiData
from module.database import DataOperator
from module.core import DownloadClient

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self, settings: Config):
        self._title_analyser = TitleParser()
        self.settings = settings

    def rss_to_datas(self, rss_link: str) -> list[BangumiData]:
        with RequestContent() as req:
            rss_torrents = req.get_torrents(rss_link)
        title_dict = {torrent.name: torrent.homepage for torrent in rss_torrents}
        with DataOperator() as op:
            new_dict = op.match_list(title_dict, rss_link)
            print(new_dict)
            if not new_dict:
                logger.debug("No new title found.")
                return []
            _id = op.gen_id()
            new_data = []
            # New List
            with RequestContent() as req:
                for raw_title, homepage in new_dict.items():
                    data = self._title_analyser.raw_parser(
                        raw=raw_title, settings=self.settings, rss_link=rss_link, _id=_id
                    )
                    if data is not None:
                        poster_link, official_title = req.get_mikan_info(homepage)
                        data.poster_link = poster_link
                        # Official title type
                        if self.settings.rss_parser.parser_type == "mikan":
                            data.official_title = official_title
                        elif self.settings.rss_parser.parser_type == "tmdb":
                            official_title, year, season = self._title_analyser.tmdb_parser()
                            data.official_title = official_title
                            data.year = year
                            data.season = season
                        else:
                            pass
                        new_data.append(data)
                        _id += 1
                        logger.debug(f"New title found: {data.official_title}")
                op.insert_list(new_data)
            return new_data

    def rss_to_data(self, url, _filter: bool = True) -> BangumiData:
        with RequestContent() as req:
            rss_torrents = req.get_torrents(url, _filter)
        for torrent in rss_torrents:
            try:
                data = self._title_analyser.raw_parser(
                    torrent.name, settings=self.settings, rss_link=url
                )
                if data is not None:
                    with DataOperator() as op:
                        _id = op.gen_id()
                        data.id = _id
                        op.insert(data)
                return data
            except Exception as e:
                logger.debug(e)

    def run(self, rss_link: str):
        logger.info("Start collecting RSS info.")
        try:
            self.rss_to_datas(rss_link)
        except Exception as e:
            logger.debug(e)


if __name__ == '__main__':
    from module.conf import settings, setup_logger
    setup_logger(settings)
    link = "https://mikanani.me/RSS/MyBangumi?token=Td8ceWZZv3s2OZm5ji9RoMer8vk5VS3xzC1Hmg8A26E%3d"
    data = RSSAnalyser(settings).rss_to_datas(link)
