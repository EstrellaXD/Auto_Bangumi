import logging

from module.database import Database, engine
from module.downloader import Client as DownlondClient
from module.models import Bangumi

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
