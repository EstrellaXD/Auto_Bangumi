import logging

from module.downloader import DownloadClient
from module.models import BangumiData
from module.database import BangumiDatabase


logger = logging.getLogger(__name__)


class TorrentManager(BangumiDatabase):
    @staticmethod
    def __match_torrents_list(data: BangumiData) -> list:
        with DownloadClient() as client:
            torrents = client.get_torrent_info()
        matched_list = []
        for torrent in torrents:
            if data.save_path == torrent.save_path:
                matched_list.append(torrent.hash)
        return matched_list

    def delete_torrents(self, _id: int | str):
        data = self.search_one(int(_id))
        if isinstance(data, BangumiData):
            hash_list = self.__match_torrents_list(data)
            with DownloadClient() as client:
                client.delete_torrent(hash_list)
            return {
                "status": "success",
                "msg": f"Delete torrents for {data.official_title}",
            }
        else:
            return data

    def delete_data(self, _id: int | str):
        data = self.search_id(int(_id))
        if isinstance(data, BangumiData):
            self.delete_one(int(_id))
            logger.info(f"Delete {data.official_title}")
            return {"status": "success", "msg": f"Delete {data.official_title}"}
        else:
            return data

    def delete_rule(self, _id: str | int, file: bool = False):
        data = self.search_id(int(_id))
        if isinstance(data, BangumiData):
            with DownloadClient() as client:
                client.remove_rule(data.rule_name)
            data.deleted = True
            self.update_one(data)
            if file:
                self.delete_torrents(data.id)
                logger.info(f"Delete rule and torrents for {data.official_title}")
                return {
                    "status": "success",
                    "msg": f"Delete rule and torrents for {data.official_title}",
                }
            logger.info(f"Delete rule for {data.official_title}")
            return {
                "status": "success",
                "msg": f"Delete rule for {data.official_title}",
            }
        else:
            return data

    def update_rule(self, data: BangumiData):
        old_data = self.search_id(data.id)
        if not old_data:
            logger.error(f"Can't find data with id {data.id}")
            return {"status": "error", "msg": f"Can't find data with id {data.id}"}
        else:
            # Set torrent path
            match_list = self.__match_torrents_list(data)
            with DownloadClient() as client:
                path = client._gen_save_path(data)
                client.move_torrent(match_list, path)
                # Set new download rule
                client.remove_rule(data.rule_name)
                client.set_rule(data)
            self.update_one(data)
            return {
                "status": "success",
                "msg": f"Set new path for {data.official_title}",
            }

    def search_all_bangumi(self):
        datas = self.search_all()
        if not datas:
            return []
        return [data for data in datas if not data.deleted]

    def search_one(self, _id: int | str):
        data = self.search_id(int(_id))
        if not data:
            logger.error(f"Can't find data with id {_id}")
            return {"status": "error", "msg": f"Can't find data with id {_id}"}
        else:
            return data
