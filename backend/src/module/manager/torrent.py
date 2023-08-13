import logging

from fastapi.responses import JSONResponse

from module.database import Database
from module.downloader import DownloadClient
from module.models import Bangumi, BangumiUpdate, ResponseModel

logger = logging.getLogger(__name__)


class TorrentManager(Database):
    @staticmethod
    def __match_torrents_list(data: Bangumi | BangumiUpdate) -> list:
        with DownloadClient() as client:
            torrents = client.get_torrent_info(status_filter=None)
        return [
            torrent.hash for torrent in torrents if torrent.save_path == data.save_path
        ]

    def delete_torrents(self, data: Bangumi, client: DownloadClient):
        hash_list = self.__match_torrents_list(data)
        if hash_list:
            client.delete_torrent(hash_list)
            logger.info(f"Delete rule and torrents for {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Delete rule and torrents for {data.official_title}",
                msg_zh=f"删除 {data.official_title} 规则和种子",
            )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find torrents for {data.official_title}",
                msg_zh=f"无法找到 {data.official_title} 的种子",
            )

    def delete_rule(self, _id: int | str, file: bool = False):
        data = self.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            with DownloadClient() as client:
                # client.remove_rule(data.rule_name)
                # client.remove_rss_feed(data.official_title)
                self.rss.delete(data.official_title)
                self.bangumi.delete_one(int(_id))
                if file:
                    torrent_message = self.delete_torrents(data, client)
                    return torrent_message
                logger.info(f"[Manager] Delete rule for {data.official_title}")
                return ResponseModel(
                    status_code=200,
                    status=True,
                    msg_en=f"Delete rule for {data.official_title}",
                    msg_zh=f"删除 {data.official_title} 规则",
                )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )

    def disable_rule(self, _id: str | int, file: bool = False):
        data = self.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            with DownloadClient() as client:
                # client.remove_rule(data.rule_name)
                data.deleted = True
                self.bangumi.update(data)
                if file:
                    torrent_message = self.delete_torrents(data, client)
                    return torrent_message
                logger.info(f"[Manager] Disable rule for {data.official_title}")
                return ResponseModel(
                    status_code=200,
                    status=True,
                    msg_en=f"Disable rule for {data.official_title}",
                    msg_zh=f"禁用 {data.official_title} 规则",
                )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )

    def enable_rule(self, _id: str | int):
        data = self.bangumi.search(int(_id))
        if isinstance(data, Bangumi):
            data.deleted = False
            self.bangumi.update(data)
            logger.info(f"[Manager] Enable rule for {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Enable rule for {data.official_title}",
                msg_zh=f"启用 {data.official_title} 规则",
            )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )

    def update_rule(self, bangumi_id, data: BangumiUpdate):
        old_data = self.bangumi.search_id(bangumi_id)
        if not old_data:
            logger.error(f"[Manager] Can't find data with {bangumi_id}")
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find data with {bangumi_id}",
                msg_zh=f"无法找到 id {bangumi_id} 的数据",
            )
        else:
            # Move torrent
            match_list = self.__match_torrents_list(old_data.save_path)
            with DownloadClient() as client:
                path = client._gen_save_path(data)
                if match_list:
                    client.move_torrent(match_list, path)
            self.bangumi.update(data)
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Update rule for {data.official_title}",
                msg_zh=f"更新 {data.official_title} 规则",
            )

    def search_all_bangumi(self):
        datas = self.bangumi.search_all()
        if not datas:
            return []
        return [data for data in datas if not data.deleted]

    def search_one(self, _id: int | str):
        data = self.bangumi.search_id(int(_id))
        if not data:
            logger.error(f"[Manager] Can't find data with {_id}")
            return JSONResponse(
                status_code=406,
                content={"msg_en": f"Can't find data with {_id}", "msg_zh": f"无法找到 id {_id} 的数据"},
            )
        else:
            return data
