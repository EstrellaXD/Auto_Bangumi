import json
from typing import TypeAlias

from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.rss import RSSAnalyser

from .provider import search_url

SEARCH_KEY = [
    "group_name",
    "title_raw",
    "season_raw",
    "subtitle",
    "source",
    "dpi",
]

BangumiJSON: TypeAlias = str


class SearchTorrent(RequestContent, RSSAnalyser):
    def search_torrents(self, rss_item: RSSItem) -> list[Torrent]:
        return self.get_torrents(rss_item.url)
        # torrents = self.get_torrents(rss_item.url)
        # return torrents

    def analyse_keyword(
            self, keywords: list[str], site: str = "mikan", limit: int = 5
    ) -> BangumiJSON:
        rss_item = search_url(site, keywords)
        torrents = self.search_torrents(rss_item)
        # yield for EventSourceResponse (Server Send)
        exist_list = set()
        for torrent in torrents:
            if len(exist_list) >= limit:
                break
            # 我新增的函数
            bangumi, special_link = self.torrent_to_bangumi(
                torrent, site, rss_item, exist_list
            )
            if bangumi:
                exist_list.add(special_link)
                yield json.dumps(bangumi.dict(), separators=(",", ":"))
            # bangumi = self.torrent_to_data(torrent=torrent, rss=rss_item)
            # if bangumi:
            #     special_link = self.special_url(bangumi, site).url
            #     if special_link not in exist_list:
            #         bangumi.rss_link = special_link
            #         exist_list.append(special_link)
            #         yield json.dumps(bangumi.dict(), separators=(",", ":"))

    @staticmethod
    def special_url(data: Bangumi, site: str) -> RSSItem:
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        url = search_url(site, keywords)
        return url

    def search_season(self, data: Bangumi, site: str = "mikan") -> list[Torrent]:
        rss_item = self.special_url(data, site)
        torrents = self.search_torrents(rss_item)
        return [torrent for torrent in torrents if data.title_raw in torrent.name]

    def torrent_to_bangumi(
            self, torrent: Torrent, site: str, rss: RSSItem, exist_list: set[str]
    ) -> tuple[Bangumi | None, str]:
        bangumi = self.raw_parser(raw=torrent.name)
        if bangumi is None:
            return None, ""
        special_link = self.special_url(bangumi, site).url
        if special_link in exist_list:
            return None, ""
        # 如果special_link已经存在（针对同一字幕组的不同集数的情况）
        self.official_title_parser(bangumi=bangumi, rss=rss, torrent=torrent)
        bangumi.rss_link = special_link
        return bangumi, special_link
