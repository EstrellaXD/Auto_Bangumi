import asyncio
import logging

from module.database import Database, engine
from module.downloader import Client as DownlondClient
from module.manager.torrent import TorrentManager
from models import Bangumi, Torrent
from module.parser import MikanParser,tmdb_parser
from module.utils import gen_save_path
from module.utils.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class BangumiManager:
    def __init__(self) -> None:
        self.torrent_manager: TorrentManager = TorrentManager()

    async def delete_rule(self, _id: int | str, file: bool = False):
        with Database(engine) as db:
            data = db.bangumi.search_id(int(_id))
        if data:
            with Database(engine) as db:
                db.bangumi.delete_one(int(_id))
                # 当 bangumi 不是聚合的时候删除 rss
                rss_item = db.bangumi_to_rss(data)
                if rss_item and rss_item.aggregate is False and rss_item.id:
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
            if file:
                torrent_message = await self.torrent_manager.delete_torrents(data)
                return torrent_message
            db.bangumi.update(data)
            logger.info(f"[Manager] Disable rule for {data.official_title}")
            return True
        else:
            return False

    async def rename(self, torrent: Torrent, bangumi: Bangumi):
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

    async def update_rule(self,  data: Bangumi):
        """更新番剧规则
        web ui 会调用这个接口, 所有传过来的 data 是一定有 id 的
        """
        with Database() as db:
            if not data.id:
                logger.error(f"[Manager] Bangumi id is required for update.")
                return False
            old_data: Bangumi | None = db.bangumi.search_id(data.id)
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
                        await self.refind_poster(data)
                    # Move torrent
                    with Database(engine) as db:
                        torrent_list = db.find_torrent_by_bangumi(old_data)

                    hash_list = [torrent.download_uid for torrent in torrent_list if torrent.download_uid]
                    new_save_path = gen_save_path(DownlondClient.config.path, data)
                    if hash_list:
                        await DownlondClient.move_torrent(hash_list, new_save_path)
                    # offset 要改为 0 ,不然会重复应用 offset
                    temp_data = data.model_copy()
                    temp_data.offset = 0
                    for torrent in torrent_list:
                        await self.rename(torrent, temp_data)

                db.bangumi.update(data)
                return True
            else:
                logger.error(f"[Manager] Can't find data with {data.official_title} {data.id}")
                return False

    async def refresh_poster(self):
        with Database() as db:
            bangumis = db.bangumi.search_all()
            tasks = []
            for bangumi in bangumis:
                if not bangumi.poster_link:
                    tasks.append(self.refind_poster(bangumi))
            await asyncio.gather(*tasks)
            db.bangumi.update_all(bangumis)
        return True

    async def refind_poster(self, bangumi: Bangumi) -> bool:
        poster_link = None
        if bangumi.mikan_id and bangumi.parser == "mikan":
            mikan_parser = MikanParser()
            await mikan_parser.poster_parser(bangumi)
        else:
            poster_link = await tmdb_parser(bangumi.official_title, "zh")
        if not poster_link:
            logger.warning(f"[Manager] Can't find poster for {bangumi.official_title}, please change it manually.")
            return False
        with Database() as db:
            db.bangumi.update(bangumi)
        return True

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
