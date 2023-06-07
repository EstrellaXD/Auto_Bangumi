import logging

from fastapi.responses import JSONResponse

from module.database import BangumiDatabase
from module.downloader import DownloadClient
from module.models import BangumiData

logger = logging.getLogger(__name__)


class TorrentManager(BangumiDatabase):
    @staticmethod
    def __match_torrents_list(data: BangumiData) -> list:
        with DownloadClient() as client:
            torrents = client.get_torrent_info(status_filter=None)
        return [torrent.hash for torrent in torrents if torrent.save_path == data.save_path]

    def delete_torrents(self, data: BangumiData, client: DownloadClient):
        hash_list = self.__match_torrents_list(data)
        if hash_list:
            client.delete_torrent(hash_list)
            logger.info(f"Delete rule and torrents for {data.official_title}")
            return f"Delete {data.official_title} torrents."
        else:
            return f"Can't find {data.official_title} torrents."

    def delete_rule(self, _id: int | str, file: bool = False):
        data = self.search_id(int(_id))
        if isinstance(data, BangumiData):
            with DownloadClient() as client:
                client.remove_rule(data.rule_name)
                client.remove_rss_feed(data.official_title)
                self.delete_one(int(_id))
                if file:
                    torrent_message = self.delete_torrents(data, client)
                    return JSONResponse(status_code=200, content={
                        "msg": f"Delete {data.official_title} rule. {torrent_message}"
                    })
                logger.info(f"[Manager] Delete rule for {data.official_title}")
                return JSONResponse(status_code=200, content={
                    "msg": f"Delete rule for {data.official_title}"
                })
        else:
            return JSONResponse(status_code=406, content={
                "msg": f"Can't find id {_id}"
            })

    def disable_rule(self, _id: str | int, file: bool = False):
        data = self.search_id(int(_id))
        if isinstance(data, BangumiData):
            with DownloadClient() as client:
                client.remove_rule(data.rule_name)
                data.deleted = True
                self.update_one(data)
                if file:
                    torrent_message = self.delete_torrents(data, client)
                    return JSONResponse(status_code=200, content={
                        "msg": f"Disable {data.official_title} rule. {torrent_message}"
                    })
                logger.info(f"[Manager] Disable rule for {data.official_title}")
                return JSONResponse(status_code=200, content={
                    "msg": f"Disable {data.official_title} rule.",
                })
        else:
            return JSONResponse(status_code=406, content={
                "msg": f"Can't find id {_id}"
            })

    def enable_rule(self, _id: str | int):
        data = self.search_id(int(_id))
        if isinstance(data, BangumiData):
            data.deleted = False
            self.update_one(data)
            with DownloadClient() as client:
                client.set_rule(data)
            logger.info(f"[Manager] Enable rule for {data.official_title}")
            return JSONResponse(status_code=200, content={
                "msg": f"Enable {data.official_title} rule.",
            })
        else:
            return JSONResponse(status_code=406, content={
                "msg": f"Can't find bangumi id {_id}"
            })

    def update_rule(self, data: BangumiData):
        old_data = self.search_id(data.id)
        if not old_data:
            logger.error(f"[Manager] Can't find data with {data.id}")
            return JSONResponse(status_code=406, content={
                "msg": f"Can't find data with {data.id}"
            })
        else:
            # Move torrent
            match_list = self.__match_torrents_list(data)
            with DownloadClient() as client:
                path = client._gen_save_path(data)
                if match_list:
                    client.move_torrent(match_list, path)
                # Set new download rule
                client.remove_rule(data.rule_name)
                client.set_rule(data)
            self.update_one(data)
            return JSONResponse(status_code=200, content={
                "msg": f"Set new path for {data.official_title}",
            })

    def search_all_bangumi(self):
        datas = self.search_all()
        if not datas:
            return []
        return [data for data in datas if not data.deleted]

    def search_one(self, _id: int | str):
        data = self.search_id(int(_id))
        if not data:
            logger.error(f"[Manager] Can't find data with {_id}")
            return {"status": "error", "msg": f"Can't find data with {_id}"}
        else:
            return data
