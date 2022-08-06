import re
import logging

from network import RequestContent
from parser import TitleParser

from conf import settings

from core import DownloadClient

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self):
        self._title_analyser = TitleParser()
        self._request = RequestContent()

    def rss_to_datas(self, bangumi_info: list) -> list:
        rss_torrents = self._request.get_torrents(settings.rss_link)
        self._request.close_session()
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
        rss_torrents = self._request.get_torrents(url)
        self._request.close_session()
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
            download_client.add_rules(bangumi_info, rss_link=settings.rss_link)
        except Exception as e:
            logger.debug(e)
        logger.info("Finished")
