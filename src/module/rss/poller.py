import re

from module.database import RSSDatabase
from module.network import RequestContent, TorrentInfo
from module.models import BangumiData, RSSTorrents
from module.conf import settings


class RSSPoller(RSSDatabase):

    @staticmethod
    def polling(rss_link, req: RequestContent) -> list[TorrentInfo]:
        return req.get_torrents(rss_link)

    @staticmethod
    def filter_torrent(data: BangumiData, torrent: TorrentInfo) -> bool:
        if data.title_raw in torrent.name:
            _filter = "|".join(data.filter)
            if not re.search(_filter, torrent.name):
                return True
            else:
                return False

    def foo(self):
        rss_datas: list[RSSTorrents] = self.get_rss_data()
        with RequestContent() as req:
            for rss_data in rss_datas:
                torrents = self.polling(rss_data.url, req)
