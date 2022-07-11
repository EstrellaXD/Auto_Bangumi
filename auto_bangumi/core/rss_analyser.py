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

    def rss_to_datas(self, bangumi_info: list):
        rss_titles = self._request.get_titles(settings.rss_link)
        self._request.close_session()
        for raw_title in rss_titles:
            extra_add = True
            if bangumi_info is not []:
                for d in bangumi_info:
                    if re.search(d["title_raw"], raw_title) is not None:
                        logger.debug(f"Had added {d['title_raw']} before")
                        extra_add = False
                        break
            if re.search(settings.not_contain, raw_title) is not None:
                extra_add = False
            if extra_add:
                data = self._title_analyser.return_dict(raw_title)
                if data is not None and data["official_title"] not in bangumi_info:
                    bangumi_info.append(data)
        return bangumi_info

    def rss_to_data(self, url):
        rss_title = self._request.get_title(url)
        self._request.close_session()
        data = self._title_analyser.return_dict(rss_title)
        return data

    def run(self, bangumi_info: list, download_client: DownloadClient):
        logger.info("Start collecting RSS info.")
        try:
            self.rss_to_datas(bangumi_info)
            download_client.add_rules(bangumi_info, rss_link=settings.rss_link)
        except Exception as e:
            logger.debug(e)
        logger.info("Finished")


if __name__ == "__main__":
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    print(settings.host_ip)
    client = DownloadClient()
    ra = RSSAnalyser()
    data = []
    ra.run(data, client)
    for d in data:
        print(d)