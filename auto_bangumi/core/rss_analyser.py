import re
import logging

from network.rss_collector import GetRssInfo
from parser.parser_api import TitleParser

from conf.conf import settings

from core.download_client import DownloadClient

logger = logging.getLogger(__name__)

class RSSAnalyser:
    def __init__(self):
        self._title_analyser = TitleParser()
        self._get_rss = GetRssInfo()

    def rss_to_data(self, bangumi_info: list):
        rss_titles = self._get_rss.get_titles(settings.rss_link)
        for raw_title in rss_titles:
            logger.info(raw_title)
            extra_add = True
            for d in bangumi_info:
                if re.search(d["title_raw"], raw_title) is not None:
                    extra_add = False
                    break
            if extra_add:
                data = self._title_analyser.return_dict(raw_title)
                if data["official_title"] not in bangumi_info:
                    bangumi_info.append(data)

    def run(self, bangumi_info: list, download_client: DownloadClient):
        self.rss_to_data(bangumi_info)
        download_client.add_rules(bangumi_info)


if __name__ == "__main__":
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    ra = RSSAnalyser()
    data = []
    ra.rss_to_data(data)
    print(data)