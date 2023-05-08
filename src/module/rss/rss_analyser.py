import logging

from module.network import RequestContent
from module.parser import TitleParser
from module.models import Config
from module.database import DataOperator
from module.core import DownloadClient

logger = logging.getLogger(__name__)


class RSSAnalyser(DownloadClient):
    def __init__(self, settings: Config):
        super().__init__(settings)
        self._title_analyser = TitleParser()
        self.settings = settings

    def rss_to_datas(self, rss_link: str):
        with RequestContent() as req:
            rss_torrents = req.get_torrents(rss_link)
        title_dict = {torrent.name: rss_link for torrent in rss_torrents}
        with DataOperator() as op:
            update_dict = op.match_list(title_dict)
            if not update_dict:
                logger.debug("No new title found.")
                return
            _id = op.gen_id()
            for raw_title in add_title_list:
                data = self._title_analyser.raw_parser(
                    raw=raw_title, _id=_id, settings=self.settings, rss_link=rss_link
                )
                if data is not None:
                    op.insert(data)
                    self.set_rule(data, rss_link)
                    _id += 1

    def rss_to_data(self, url, _filter: bool = True):
        with RequestContent() as req:
            rss_torrents = req.get_torrents(url, _filter)
        for torrent in rss_torrents:
            try:
                data = self._title_analyser.raw_parser(
                    torrent.name, settings=self.settings, rss_link=url
                )
                self.set_rule(data, url)
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
    with RSSAnalyser(settings) as analyser:
        analyser.rss_to_datas(link)
