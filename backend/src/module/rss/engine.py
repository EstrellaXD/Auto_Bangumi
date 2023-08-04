import re
import logging

from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent, TorrentInfo
from module.downloader import DownloadClient

from module.database.combine import Database


class RSSEngine(Database):
    @staticmethod
    def _get_torrents(rss_link: str) -> list[Torrent]:
        with RequestContent() as req:
            torrent_infos = req.get_torrents(rss_link)
        torrents: list[Torrent] = []
        for torrent_info in torrent_infos:
            torrents.append(
                Torrent(
                    name=torrent_info.name,
                    url=torrent_info.torrent_link,
                    homepage=torrent_info.homepage,
                )
            )
        return torrents

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

    def match_torrent(self, torrent: Torrent):
        matched: Bangumi = self.bangumi.match_torrent(torrent.name)
        if matched:
            torrent.refer_id = matched.id
            torrent.save_path = matched.save_path
            with RequestContent() as req:
                torrent_file = req.get_content(torrent.url)
            with DownloadClient() as client:
                client.add_torrent(
                    {"torrent_files": torrent_file, "save_path": torrent.save_path}
                )
                torrent.downloaded = True

    def run(self):
        # Get All RSS Items
        rss_items: list[RSSItem] = self.rss.search_active()
        # From RSS Items, get all torrents
        for rss_item in rss_items:
            new_torrents = self.pull_rss(rss_item)
            # Get all enabled bangumi data
            for torrent in new_torrents:
                self.match_torrent(torrent)
            self.torrent.add_all(new_torrents)


if __name__ == "__main__":
    with RSSEngine() as engine:
        engine.run()
