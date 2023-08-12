import re
import logging

from typing import Optional

from module.models import Bangumi, RSSItem, Torrent, ResponseModel
from module.network import RequestContent
from module.downloader import DownloadClient

from module.database import Database, engine

logger = logging.getLogger(__name__)


class RSSEngine(Database):
    def __init__(self, _engine=engine):
        super().__init__(_engine)

    @staticmethod
    def _get_torrents(rss: RSSItem) -> list[Torrent]:
        with RequestContent() as req:
            torrents = req.get_torrents(rss.url)
            # Add RSS ID
            for torrent in torrents:
                torrent.rss_id = rss.id
        return torrents

    def get_combine_rss(self) -> list[RSSItem]:
        return self.rss.get_combine()

    def get_rss_torrents(self, rss_id: int) -> list[Torrent]:
        rss = self.rss.search_id(rss_id)
        if rss:
            return self.torrent.search_rss(rss_id)
        else:
            return []

    def add_rss(self, rss_link: str, name: str | None = None, combine: bool = True):
        if not name:
            with RequestContent() as req:
                name = req.get_rss_title(rss_link)
        rss_data = RSSItem(item_path=name, url=rss_link, combine=combine)
        if self.rss.add(rss_data):
            return ResponseModel(
                status=True,
                status_code=200,
                msg_en="RSS added successfully.",
                msg_zh="RSS 添加成功。",
            )
        else:
            return ResponseModel(
                status=False,
                status_code=400,
                msg_en="RSS added failed.",
                msg_zh="RSS 添加失败。",
            )

    def pull_rss(self, rss_item: RSSItem) -> list[Torrent]:
        torrents = self._get_torrents(rss_item)
        new_torrents = self.torrent.check_new(torrents)
        return new_torrents

    def match_torrent(self, torrent: Torrent) -> Optional[Bangumi]:
        matched: Bangumi = self.bangumi.match_torrent(torrent.name)
        if matched:
            _filter = matched.filter.replace(",", "|")
            if not re.search(_filter, torrent.name, re.IGNORECASE):
                torrent.bangumi_id = matched.id
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
        logger.debug(f"[Engine] Get {len(rss_items)} RSS items")
        for rss_item in rss_items:
            new_torrents = self.pull_rss(rss_item)
            # Get all enabled bangumi data
            for torrent in new_torrents:
                matched_data = self.match_torrent(torrent)
                if matched_data:
                    if client.add_torrent(torrent, matched_data):
                        logger.debug(f"[Engine] Add torrent {torrent.name} to client")
                        torrent.downloaded = True
            # Add all torrents to database
            self.torrent.add_all(new_torrents)
