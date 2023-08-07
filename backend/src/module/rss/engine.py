import re
import logging

from typing import Optional

from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.downloader import DownloadClient

from module.database import Database, engine

logger = logging.getLogger(__name__)


class RSSEngine(Database):
    def __init__(self, _engine=engine):
        super().__init__(_engine)

    @staticmethod
    def _get_torrents(rss_link: str) -> list[Torrent]:
        with RequestContent() as req:
            torrents = req.get_torrents(rss_link)
        return torrents

    def get_combine_rss(self) -> list[RSSItem]:
        return self.rss.get_combine()

    def add_rss(self, rss_link: str, name: str | None = None, combine: bool = True):
        if not name:
            with RequestContent() as req:
                name = req.get_rss_title(rss_link)
        rss_data = RSSItem(item_path=name, url=rss_link, combine=combine)
        self.rss.add(rss_data)

    def pull_rss(self, rss_item: RSSItem) -> list[Torrent]:
        torrents = self._get_torrents(rss_item.url)
        new_torrents = self.torrent.check_new(torrents)
        return new_torrents

    def match_torrent(self, torrent: Torrent) -> Optional[Bangumi]:
        matched: Bangumi = self.bangumi.match_torrent(torrent.name)
        if matched:
            _filter = matched.filter.replace(",", "|")
            if not re.search(_filter, torrent.name, re.IGNORECASE):
                torrent.refer_id = matched.id
                torrent.save_path = matched.save_path
                return matched
        return None

    def refresh_rss(self, client: DownloadClient, rss_id: Optional[int] = None):
        # Get All RSS Items
        if not rss_id:
            rss_items: list[RSSItem] = self.rss.search_active()
        else:
            rss_item = self.rss.search_id(rss_id)
            rss_items = [rss_item] if rss_item else []
        # From RSS Items, get all torrents
        for rss_item in rss_items:
            new_torrents = self.pull_rss(rss_item)
            # Get all enabled bangumi data
            for torrent in new_torrents:
                matched_data = self.match_torrent(torrent)
                if matched_data:
                    if client.add_torrent(torrent, matched_data):
                        torrent.downloaded = True
            # Add all torrents to database
            self.torrent.add_all(new_torrents)
