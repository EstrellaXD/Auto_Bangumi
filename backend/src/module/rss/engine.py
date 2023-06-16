import re

from module.database import RSSDatabase, BangumiDatabase, TorrentDatabase
from module.models import BangumiData, RSSItem, TorrentData
from module.network import RequestContent, TorrentInfo


class RSSEngine(RequestContent):

    @staticmethod
    def _get_rss_items() -> list[RSSItem]:
        with RSSDatabase() as db:
            return db.get_all()

    @staticmethod
    def _get_bangumi_data(rss_link: str) -> list[BangumiData]:
        with BangumiDatabase() as db:
            return db.get_rss_data(rss_link)

    def add_rss(self, rss_link: str, name: str, combine: bool):
        if not name:
            name = self.get_rss_title(rss_link)
        insert_data = RSSItem(item_path=name, url=rss_link, combine=combine)
        with RSSDatabase() as db:
            db.insert_one(insert_data)

    def pull_rss(self, rss_item: RSSItem) -> list[TorrentInfo]:
        torrents = self.get_torrents(rss_item.url)
        return torrents

    @staticmethod
    def match_torrent(torrent: TorrentInfo) -> TorrentData | None:
        with BangumiDatabase() as db:
            bangumi_data = db.match_torrent(torrent.name)
            if bangumi_data:
                _filter = "|".join(bangumi_data.filter)
                if re.search(_filter, torrent.name):
                    return None
                else:
                    return TorrentData(
                        name=torrent.name,
                        url=torrent.torrent_link,
                    )
            return None

    @staticmethod
    def filter_torrent(torrents: list[TorrentInfo]) -> list[TorrentInfo]:
        with TorrentDatabase() as db:
            in_db_torrents = db.get_all()
        in_db_torrents = [x.name for x in in_db_torrents]
        i = 0
        while i < len(torrents):
            torrent = torrents[i]
            if torrent.name in in_db_torrents:
                torrents.pop(i)
            i += 1
        return torrents

    def run(self):
        # Get All RSS Items
        rss_items: list[RSSItem] = self._get_rss_items()
        # From RSS Items, get all torrents
        for rss_item in rss_items:
            torrents = self.get_torrents(rss_item.url)
            self.filter_torrent(torrents)
            # Get all enabled bangumi data
            matched_torrents = []
            for torrent in torrents:
                matched_torrent = self.match_torrent(torrent)
                if matched_torrent:
                    matched_torrents.append(matched_torrent)
            # Add to database
            with TorrentDatabase() as db:
                db.insert_many(matched_torrents)
            return matched_torrents
