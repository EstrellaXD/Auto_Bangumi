import asyncio
import logging

from module.conf import PLATFORM
from module.database import Database, engine
from module.downloader import DownloadClient
from module.models import Bangumi, BangumiUpdate, ResponseModel
from module.parser import TmdbParser
from module.utils.bangumi_data import get_hash

if PLATFORM == "Windows":
    from pathlib import PureWindowsPath as Path
else:
    from pathlib import Path
logger = logging.getLogger(__name__)


class TorrentManager():
    @staticmethod
    async def __match_torrents_list(data: Bangumi | BangumiUpdate) -> list[str]:
        async with DownloadClient() as client:
            torrents = await client.get_torrent_info(status_filter=None)
        return [
            torrent["hash"] for torrent in torrents if torrent["save_path"] == data.save_path
        ]

    async def delete_torrents(self, data: Bangumi, client: DownloadClient):
        hash_list = await self.__match_torrents_list(data)
        if hash_list:
            await client.delete_torrent(hash_list)
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

    async def delete_rule(self, _id: int | str, file: bool = False):
        with Database(engine) as db:
            data = db.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
           async with DownloadClient() as client:
                with Database(engine) as db:
                    # bangumi 删了怎么删 rss?
                    # db.rss.delete(data.official_title)
                    db.bangumi.delete_one(int(_id))
                if file:
                    torrent_message = await self.delete_torrents(data, client)
                logger.info(f"[Manager] Delete rule for {data.official_title}")
                return ResponseModel(
                    status_code=200,
                    status=True,
                    msg_en=f"Delete rule for {data.official_title}. {torrent_message.msg_en if file else ''}",
                    msg_zh=f"删除 {data.official_title} 规则。{torrent_message.msg_zh if file else ''}",
                )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )

    async def disable_rule(self, _id: str | int, file: bool = False):
        with Database() as db:
            data = db.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            async with DownloadClient() as client:
                # client.remove_rule(data.rule_name)
                data.deleted = True
                db.bangumi.update(data)
                if file:
                    torrent_message = await self.delete_torrents(data, client)
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

    async def enable_rule(self, _id: str | int):

        with Database() as db:
            data = db.bangumi.search_id(int(_id))
            if data:
                data.deleted = False
                db.bangumi.update(data)
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

    async def update_rule(self, bangumi_id:int, data: BangumiUpdate):
        with Database() as db:
            old_data: Bangumi|None = db.bangumi.search_id(bangumi_id)
            if old_data:
                # Move torrent
                hash_list = await self.__match_torrents_list(old_data)
                async with DownloadClient() as client:
                    path = client._path_parser.gen_save_path(data)
                    if hash_list:
                        await client.move_torrent(hash_list, path)
                data.save_path = path
                torrent_list = db.torrent.search_bangumi(old_data.id)
                # 有bug,这会累加 offset,故设为0
                data.offset = 0
                for torrent in torrent_list:
                    if get_hash(torrent.url) in hash_list:
                        torrent.downloaded = False
                db.bangumi.update(data, bangumi_id)
                db.torrent.add_all(torrent_list)
                return ResponseModel(
                    status_code=200,
                    status=True,
                    msg_en=f"Update rule for {data.official_title}",
                    msg_zh=f"更新 {data.official_title} 规则",
                )
            else:
                logger.error(f"[Manager] Can't find data with {bangumi_id}")
                return ResponseModel(
                    status_code=406,
                    status=False,
                    msg_en=f"Can't find data with {bangumi_id}",
                    msg_zh=f"无法找到 id {bangumi_id} 的数据",
                )

    async def refresh_poster(self):
        with Database() as db:
            bangumis = db.bangumi.search_all()
            tasks  = []
            for bangumi in bangumis:
                if not bangumi.poster_link:
                    tasks.append(TmdbParser().poster_parser(bangumi))
            await asyncio.gather(*tasks)
            db.bangumi.update_all(bangumis)
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en="Refresh poster link successfully.",
            msg_zh="刷新海报链接成功。",
        )

    async def refind_poster(self, bangumi_id: int):
        with Database() as db:
            bangumi = db.bangumi.search_id(bangumi_id)
            if bangumi:
                await TmdbParser().poster_parser(bangumi)
                db.bangumi.update(bangumi)
                return ResponseModel(
                    status_code=200,
                    status=True,
                    msg_en="Refresh poster link successfully.",
                    msg_zh="刷新海报链接成功。",
                )

    def search_all_bangumi(self):
        with Database() as db:
            datas = db.bangumi.search_all()
            if not datas:
                return []
            return [data for data in datas if not data.deleted]

    def search_one(self, _id: int | str):

        with Database() as db:
            data = db.bangumi.search_id(int(_id))
            if not data:
                logger.error(f"[Manager] Can't find data with {_id}")
                return ResponseModel(
                    status_code=406,
                    status=False,
                    msg_en=f"Can't find data with {_id}",
                    msg_zh=f"无法找到 id {_id} 的数据",
                )
            else:
                return data


if __name__ == "__main__":
    manager = TorrentManager()
    asyncio.run(manager.refresh_poster())
