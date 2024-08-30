import asyncio
import logging

from module.database import Database, engine
from module.downloader import DownloadClient
from module.manager.renamer import Renamer
from module.models import Bangumi, BangumiUpdate, ResponseModel
from module.parser import TmdbParser
from module.utils.bangumi_data import get_hash

logger = logging.getLogger(__name__)


class TorrentManager:
    @staticmethod
    async def __match_torrents_list(data: Bangumi | BangumiUpdate) -> list[str]:
        """find torrent save in same path

        Args:
            data: [TODO:description]

        Returns:
            [
        """
        async with DownloadClient() as client:
            torrents = await client.get_torrent_info(status_filter=None)
        return [
            torrent["hash"]
            for torrent in torrents
            if torrent["save_path"] == data.save_path
        ]

    async def delete_torrents(self, data: Bangumi, client: DownloadClient):
        data.save_path = client._path_parser.gen_save_path(data)
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
            torrent_message = None
        if isinstance(data, Bangumi):
            async with DownloadClient() as client:
                with Database(engine) as db:
                    # bangumi 删了怎么删 rss?
                    # db.rss.delete(data.official_title)
                    db.bangumi.delete_one(int(_id))
                    rss_item = db.rss.search_url(data.rss_link)
                    if rss_item and rss_item.aggregate is False:
                        db.rss.delete(rss_item.id)

                if file:
                    torrent_message = await self.delete_torrents(data, client)
                logger.info(f"[Manager] Delete rule for {data.official_title}")
            return data, torrent_message
        return None, None

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

    async def offset_rename(self,data:Bangumi,path,hash_list):
        renamer = Renamer()
        # data.offset = data.offset - 20000
        if data.offset<-2000:
            await asyncio.sleep(30)
        renamer_task = []
        async with DownloadClient() as client:
            for torrent_hash in hash_list:
                renamer_info = await renamer.gen_renamer_info(
                    client=client,
                    torrent_hash=torrent_hash,
                    bangumi=data,
                    torrent_item="",
                    save_path=path,
                )
                renamer_task.append(
                    renamer.rename_by_info(
                        client,
                        renamer_info,
                    )
                )
            await asyncio.gather(*renamer_task, return_exceptions=True)

    async def update_rule(self, bangumi_id: int, data: BangumiUpdate):
        with Database() as db:
            old_data: Bangumi | None = db.bangumi.search_id(bangumi_id)
            renamer = Renamer()
            if old_data:
                # 当只改Filter的时候只改database
                # 当offset 的时候 只改torrent
                if (
                    old_data.official_title != data.official_title
                    or old_data.year != data.year
                    or old_data.season != data.season
                    or old_data.offset != data.offset
                ):
                    # Move torrent
                    async with DownloadClient() as client:
                        old_data.save_path = client._path_parser.gen_save_path(old_data)
                        hash_list = await self.__match_torrents_list(old_data)
                        path = client._path_parser.gen_save_path(data)
                        data.save_path = path
                        temp_data = Bangumi(offset=data.offset - old_data.offset)
                        if temp_data.offset != 0:
                            temp_data.offset = 10000 + temp_data.offset

                        if hash_list:
                            await client.move_torrent(hash_list, path)
                        # save_path改动后名命名一次
                        await self.offset_rename(temp_data,path,hash_list)
                        if temp_data.offset != 0:
                            temp_data.offset = -10000
                            # 太快了会导致renamer 的数据是之前的
                            asyncio.create_task(self.offset_rename(temp_data,path,hash_list))

                db.bangumi.update(data, bangumi_id)
                return True
            else:
                logger.error(f"[Manager] Can't find data with {bangumi_id}")
                return False

    async def refresh_poster(self):
        with Database() as db:
            bangumis = db.bangumi.search_all()
            tasks = []
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
