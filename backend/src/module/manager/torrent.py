import asyncio
import logging

from module.database import Database, engine
from module.downloader import Client as DownlondClient
from module.manager.renamer import Renamer
from module.models import Bangumi, BangumiUpdate
from module.parser import TmdbParser

logger = logging.getLogger(__name__)


class TorrentManager:
    def __init__(self) -> None:
        self.tmdb_parser:TmdbParser = TmdbParser()

    @staticmethod
    async def __match_torrents_list(data: Bangumi | BangumiUpdate) -> list[str]:
        """find torrent save in same path

        Args:
            data: [TODO:description]

        Returns:
            [
        """
        async with DownlondClient:
            torrents = await DownlondClient.get_torrent_info(status_filter=None)
        return [
            torrent["hash"]
            for torrent in torrents
            if torrent["save_path"] == data.save_path
        ]

    async def delete_torrents(self, data: Bangumi) -> bool:
        """删除和 bangumi 相同路径的种子

        Args:
            data: Bangumi

        Returns:
            [TODO:return]
        """
        # 删除 bangumi
        async with DownlondClient:
            data.save_path = DownlondClient._path_parser.gen_save_path(data)
            hash_list = await self.__match_torrents_list(data)
            if hash_list:
                res = await DownlondClient.delete_torrent(hash_list)
                if res:
                    with Database() as database:
                        for _hash in hash_list:
                            if torrent_item := database.torrent.search_hash(_hash):
                                database.torrent.delete(torrent_item.id)

                logger.info(f"Delete rule and torrents for {data.official_title}")
                return True
            else:
                return False

    async def delete_rule(self, _id: int | str, file: bool = False):
        with Database(engine) as db:
            data = db.bangumi.search_id(int(_id))
        if data:
            async with DownlondClient:
                with Database(engine) as db:
                    db.bangumi.delete_one(int(_id))
                    # 当 bangumi 不是聚合的时候删除 rss
                    rss_item = db.bangumi_to_rss(data)
                    if rss_item and rss_item.aggregate is False:
                        db.rss.delete(rss_item.id)
                if file:
                    await self.delete_torrents(data)
                logger.info(f"[Manager] Delete rule for {data.official_title}")
            return data
        return None

    async def disable_rule(self, _id: str | int, file: bool = False) -> bool:
        with Database() as db:
            data = db.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            async with DownlondClient:
                # client.remove_rule(data.rule_name)
                data.deleted = True
                db.bangumi.update(data)
                if file:
                    torrent_message = await self.delete_torrents(data)
                    return torrent_message
                logger.info(f"[Manager] Disable rule for {data.official_title}")
                return True
        else:
            return False

    async def enable_rule(self, _id: str | int):

        with Database() as db:
            data = db.bangumi.search_id(int(_id))
            if data:
                data.deleted = False
                db.bangumi.update(data)
                logger.info(f"[Manager] Enable rule for {data.official_title}")
                return True
            else:
                return False

    async def rename(self, save_path: str, hash_list: list[str]):
        renamer = Renamer()
        renamer_task = []
        async with DownlondClient:
            for torrent_hash in hash_list:

                file_contents = await renamer.get_torrent_files(torrent_hash)
                renamer_task.append(
                    renamer.rename_files(
                        torrent_hash,
                        files_path=file_contents,
                        save_path=save_path,
                    )
                )
            await asyncio.gather(*renamer_task)

    async def update_rule(self, bangumi_id: int, data: BangumiUpdate):
        with Database() as db:
            old_data: Bangumi | None = db.bangumi.search_id(bangumi_id)
            if old_data:
                # 当只改Filter,offset的时候只改database
                if (
                    old_data.official_title != data.official_title
                    or old_data.year != data.year
                    or old_data.season != data.season
                ):
                    # 名字改了, 年份改了, 季改了
                    # 名字改的时候,刷新一下海报
                    if old_data.official_title != data.official_title:
                        await self.tmdb_parser.poster_parser(data)
                    # Move torrent
                    async with DownlondClient:
                        old_data.save_path = DownlondClient._path_parser.gen_save_path(
                            old_data
                        )
                        hash_list = await self.__match_torrents_list(old_data)
                        new_save_path = DownlondClient._path_parser.gen_save_path(data)

                        if hash_list:
                            await DownlondClient.move_torrent(hash_list, new_save_path)
                        # save_path改动后名命名一次
                        await self.rename(new_save_path, hash_list)
                        await asyncio.sleep(1)


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
                    tasks.append(self.tmdb_parser.poster_parser(bangumi))
            await asyncio.gather(*tasks)
            db.bangumi.update_all(bangumis)
        return True

    async def refind_poster(self, bangumi_id: int) -> bool:
        with Database() as db:
            bangumi = db.bangumi.search_id(bangumi_id)
            if bangumi:
                await self.tmdb_parser.poster_parser(bangumi)
                db.bangumi.update(bangumi)
                return True
        return False

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
                return None
            else:
                return data


if __name__ == "__main__":
    manager = TorrentManager()
    asyncio.run(manager.refresh_poster())
