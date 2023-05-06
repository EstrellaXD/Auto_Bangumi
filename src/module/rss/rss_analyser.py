import re
import logging

from module.network import RequestContent
from module.parser import TitleParser
from module.models import BangumiData, Config
from module.database import DataOperator

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self, settings: Config):
        self._title_analyser = TitleParser()
        self.settings = settings

    def rss_to_datas(self, rss_link: str) -> list[BangumiData]:
        with RequestContent() as req:
            rss_torrents = req.get_torrents(rss_link)
        title_list = [torrent.name for torrent in rss_torrents]
        data_list = []
        with DataOperator() as op:
            add_title_list = op.not_exist_titles(title_list)
            _id = op.gen_id()
            for raw_title in add_title_list:
                data = self._title_analyser.raw_parser(
                    raw=raw_title, _id=_id, settings=self.settings
                )
                if data is not None and op.match_title(data.official_title) is None:
                    data_list.append(data)
                    _id += 1
            op.insert_list(data_list)
        return data_list

    def rss_to_data(self, url, _filter: bool = True) -> BangumiData:
        with RequestContent() as req:
            rss_torrents = req.get_torrents(url, _filter)
        for torrent in rss_torrents:
            try:
                data = self._title_analyser.raw_parser(
                    torrent.name, settings=self.settings
                )
                return data
            except Exception as e:
                logger.debug(e)

    def run(self, rss_link: str):
        logger.info("Start collecting RSS info.")
        try:
            return self.rss_to_datas(rss_link)
        except Exception as e:
            logger.debug(e)
