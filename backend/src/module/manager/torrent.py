import logging

from module.database import Database, engine
from module.downloader import Client as DownlondClient
from module.downloader import download_queue
from module.models import Bangumi, Torrent
from module.network import RequestContent

logger = logging.getLogger(__name__)


class TorrentManager:
    # def __init__(self) -> None:
    #     self.tmdb_parser: TmdbParser = TmdbParser()

    async def delete_torrents(self, data: Bangumi) -> bool:
        """删除和 bangumi 相同路径的种子

        Args:
            data: Bangumi

        Returns:
            [TODO:return]
        """
        # 删除 bangumi
        # data.save_path = DownlondClient._path_parser.gen_save_path(data)
        with Database(engine) as db:
            torrent_list = db.find_torrent_by_bangumi(data)
            hash_list = [
                torrent.download_uid for torrent in torrent_list if torrent.download_uid
            ]
        if hash_list:
            res = await DownlondClient.delete_torrent(hash_list)
            if res:
                with Database() as database:
                    for _hash in hash_list:
                        database.torrent.delete_by_duid(_hash)
            logger.info(f"Delete rule and torrents for {data.official_title}")
            return True
        return False

    async def delete_torrent(self,url:str)->bool:
        with Database(engine) as db:
            torrent =  db.torrent.search_by_url(url)
            if torrent and torrent.download_uid:
                res = await DownlondClient.delete_torrent(torrent.download_uid)
            res = db.torrent.delete_by_url(url)
            return res

    def download_torrent(self, _id:int,torrent: Torrent) -> bool:
        """下载种子
        Args:
            bangumi: 番剧信息
        """
        with Database() as db:
            bangumi = db.bangumi.search_id(int(_id))
            if not bangumi:
                logger.error(f"[Manager] Can't find data with {_id}")
                return False

        # 构造一个 torrent
        torrent.bangumi_official_title = bangumi.official_title
        torrent.bangumi_season = bangumi.season
        torrent.rss_link = bangumi.rss_link

        download_queue.add(torrent, bangumi)
        return True

    async def fetch_all_bangumi_torrents(self,_id:int)->list[Torrent]:
        # 先拉一下 rss
        # 然后从数据库找
        # 最后返回一个 torrent list
        with Database() as db:
            bangumi = db.bangumi.search_id(int(_id))
            if not bangumi:
                logger.error(f"[Manager] Can't find data with {_id}")
                return []
            exist_torrents: list[Torrent] = db.find_torrent_by_bangumi(bangumi)
            url = bangumi.rss_link
        existing_urls = {torrent.url for torrent in exist_torrents}
        async with RequestContent() as req:
            torrents = await req.get_torrents(url)
        title_raws = bangumi.title_raw.split(",")
        for torrent in torrents:
            if torrent.url in existing_urls:
                continue
            for title in title_raws:
                if title in torrent.name:
                    exist_torrents.append(torrent)
                    existing_urls.add(torrent.url)
                    break
        exist_torrents.sort(key=lambda x: x.name, reverse=True)
        return exist_torrents

    async def disable_torrent(self,url,name,_id:int)->bool:
        with Database(engine) as db:
            bangumi = db.bangumi.search_id(_id)
            if not bangumi:
                return False
            torrent = db.torrent.search_by_url(url)
            if not torrent:
                torrent = Torrent(url=url,name=name)
            torrent.downloaded = True
            torrent.renamed = True
            torrent.bangumi_official_title = bangumi.official_title
            torrent.bangumi_season = bangumi.season
            torrent.rss_link = bangumi.rss_link
            db.torrent.add(torrent)
            return True
