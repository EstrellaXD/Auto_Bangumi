import asyncio
import logging

from module.database import Database, engine
from module.downloader import Client as DownlondClient
from module.models import Bangumi, BangumiUpdate, Torrent
from module.parser import TmdbParser
from module.utils import gen_save_path
from module.conf import settings
from module.manager.torrent import TorrentManager
from module.utils.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class BangumiManager:
    def __init__(self) -> None:
        self.tmdb_parser: TmdbParser = TmdbParser()
        self.torrent_manager: TorrentManager = TorrentManager()

    async def delete_rule(self, _id: int | str, file: bool = False):
        with Database(engine) as db:
            data = db.bangumi.search_id(int(_id))
        if data:
            with Database(engine) as db:
                db.bangumi.delete_one(int(_id))
                # 当 bangumi 不是聚合的时候删除 rss
                rss_item = db.bangumi_to_rss(data)
                if rss_item and rss_item.aggregate is False:
                    db.rss.delete(rss_item.id)
            if file:
                await self.torrent_manager.delete_torrents(data)
            logger.info(f"[Manager] Delete rule for {data.official_title}")
            return data
        return None

    async def disable_rule(self, _id: str | int, file: bool = False) -> bool:
        with Database() as db:
            data = db.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            data.deleted = True
            db.bangumi.update(data)
            if file:
                torrent_message = await self.torrent_manager.delete_torrents(data)
                return torrent_message
            logger.info(f"[Manager] Disable rule for {data.official_title}")
            return True
        else:
            return False

    async def rename(self, torrent:Torrent,bangumi:Bangumi|BangumiUpdate):
        """重命名种子文件
        Args:
            torrent: 种子信息
            bangumi: 番剧信息
        """
        try:
            event = Event(
                type=EventType.DOWNLOAD_COMPLETED,
                data={"torrent": torrent, "bangumi": bangumi},
            )
            await event_bus.publish(event)
            logger.debug(f"[Download Controller] 已发布下载开始事件: {torrent.name}")

        except Exception as e:
            logger.error(f"[Download Controller] 发布下载开始事件失败: {e}")

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
                    with Database(engine) as db:
                        torrent_list = db.find_torrent_by_bangumi(old_data)

                    hash_list = [torrent.download_uid for torrent in torrent_list]
                    new_save_path = gen_save_path(settings.downloader.path, data)
                    if hash_list:
                        await DownlondClient.move_torrent(hash_list, new_save_path)
                    for torrent in torrent_list:
                        await self.rename(torrent, data)

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
