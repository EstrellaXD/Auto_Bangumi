import json
from typing import TypeAlias

from module.conf import settings
from module.models import Bangumi, RSSItem, Torrent
from module.network import RequestContent
from module.rss import RSSAnalyser

from module.manager.renamer import Renamer
from module.parser import TitleParser
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


class SearchTorrent(RequestContent, RSSAnalyser, TitleParser, Renamer):
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
        exist_list = []
        for torrent in torrents:
            if len(exist_list) >= limit:
                break
            bangumi = self.torrent_to_data(torrent=torrent, rss=rss_item)
            if bangumi:
                special_link = self.special_url(bangumi, site).url
                if special_link not in exist_list:
                    bangumi.rss_link = special_link
                    exist_list.append(special_link)
                    yield json.dumps(bangumi.dict(), separators=(",", ":"))

    @staticmethod
    def special_url(data: Bangumi, site: str) -> RSSItem:
        keywords = [getattr(data, key) for key in SEARCH_KEY if getattr(data, key)]
        url = search_url(site, keywords)
        return url

    def check_torrent_duplicate(self, bangumi: Bangumi, torrent: Torrent):
        rename_method = settings.bangumi_manage.rename_method
        # 查找视频是否包含关键字
        keywords = ['内嵌','外挂','封装','MKV','内挂']
        suffix = 'mp4'
        for item1 in keywords:
            if(item1 in torrent.name):
                suffix = 'mkv'
        # 解析视频
        ep = self.torrent_parser(
            torrent_path=f"{torrent.name}.{suffix}"
        )
        if(ep):
            ep_name = self.gen_path(ep, bangumi.official_title, method=rename_method)
            torrent.bangumi_id = bangumi.id
            torrent.save_path = f'{bangumi.save_path}/{ep_name}'
            return torrent
        return False
    
    def search_season(self, data: Bangumi, site: str = "mikan") -> list[Torrent]:
        rss_item = self.special_url(data, site)
        torrents = self.search_torrents(rss_item)
        new_torrents = []
        for item1 in torrents:
            if data.title_raw in item1.name:
                res = self.check_torrent_duplicate(data, item1)
                if(res):
                    new_torrents.append(res)
        return new_torrents