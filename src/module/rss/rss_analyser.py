import re
import logging
from module.network import RequestContent
from module.parser import TitleParser

from module.conf import settings, RSS_LINK

from module.core import DownloadClient

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self):
        self._title_analyser = TitleParser()

    def rss_to_datas(self, bangumi_info: list) -> list:
        with RequestContent() as req:
            rss_torrents = req.get_torrents(RSS_LINK)
        for torrent in rss_torrents:
            raw_title = torrent.name
            extra_add = True
            if bangumi_info is not []:
                for d in bangumi_info:
                    if re.search(d["title_raw"], raw_title) is not None:
                        logger.debug(f"Had added {d['title_raw']} in auto_download rule before")
                        extra_add = False
                        break
            if extra_add:
                data = self._title_analyser.return_dict(raw_title)
                if data is not None and data["official_title"] not in bangumi_info:
                    bangumi_info.append(data)
        return bangumi_info

    def rss_to_data(self, url) -> dict:
        with RequestContent() as req:
            rss_torrents = req.get_torrents(url)
        for torrent in rss_torrents:
            try:
                data = self._title_analyser.return_dict(torrent.name)
                return data
            except Exception as e:
                logger.debug(e)

    def run(self, bangumi_info: list, download_client: DownloadClient):
        logger.info("Start collecting RSS info.")
        try:
            self.rss_to_datas(bangumi_info)
            download_client.add_rules(bangumi_info, rss_link=RSS_LINK)
        except Exception as e:
            logger.debug(e)
        logger.info("Finished")
