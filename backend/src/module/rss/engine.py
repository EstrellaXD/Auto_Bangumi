import logging
import asyncio
import re
from typing import Optional, Callable

from module.database import Database, engine
from module.downloader import DownloadClient
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent
from module.conf import settings

logger = logging.getLogger(__name__)


class RSSEngine:
    def __init__(self):
        self._to_refresh = False
        self.db_status = False

    async def rss_poller(self, callback: Callable = None):
        # Main RSS Loop
        while True:
            with Database() as database:
                rss_items = database.rss.search_active()
                if rss_items:
                    tasks = []
                    for item in rss_items:
                        tasks.append(self.pull_rss(item, database, callback))
                    await asyncio.gather(*tasks)
            await asyncio.sleep(settings.program.rss_time)

    @staticmethod
    async def _get_torrents(rss: RSSItem) -> list[Torrent]:
        async with RequestContent() as req:
            torrents = await req.get_torrents(rss.url)
            # Add RSS ID
            for torrent in torrents:
                torrent.rss_id = rss.id
            return torrents

    async def pull_rss(
        self, rss_item: RSSItem, database: Database = None, callback: Callable = None, **kwargs
    ) -> list[Torrent]:
        torrents = await self._get_torrents(rss_item)
        new_torrents = database.torrent.check_new(torrents)
        if callback:
            await callback(rss_item, new_torrents, **kwargs)
        database.torrent.add_all(new_torrents)
        return new_torrents

    @staticmethod
    def match_torrent(torrent: Torrent, database: Database) -> Optional[Bangumi]:
        matched: Bangumi = database.bangumi.match_torrent(torrent.name)
        if matched:
            if matched.filter == "":
                return matched
            _filter = matched.filter.replace(",", "|")
            if not re.search(_filter, torrent.name, re.IGNORECASE):
                torrent.bangumi_id = matched.id
                return matched
        return None

    async def refresh_rss(
        self,
        client: DownloadClient,
        database: Database = None,
        rss_id: Optional[int] = None,
        callback: Callable = None,
    ):
        # Connect to Database if not connected
        if not database:
            database = self.__connect_database()
            self.db_status = True
        # Get All RSS Items
        if not rss_id:
            rss_items: list[RSSItem] = database.rss.search_active()
        else:
            rss_items = [database.rss.search_id(rss_id)]
        # From RSS Items, get all torrents
        logger.debug(f"[Engine] Get {len(rss_items)} RSS items")
        tasks = []
        for rss_item in rss_items:
            tasks.append(
                self.pull_rss(
                    rss_item=rss_item,
                    database=database,
                    callback=callback,
                    client=client,
                )
            )
        await asyncio.gather(*tasks)
        # Close Database if not connected
        if self.db_status:
            database.close()

    @staticmethod
    async def download_bangumi(bangumi: Bangumi, database: Database):
        async with RequestContent() as req:
            torrents = await req.get_torrents(
                bangumi.rss_link, bangumi.filter.replace(",", "|")
            )
            if torrents:
                async with DownloadClient() as client:
                    await client.add_torrents(torrents, bangumi)
                    database.torrent.add_all(torrents)
                    return ResponseModel(
                        status=True,
                        status_code=200,
                        msg_en=f"[Engine] Download {bangumi.official_title} successfully.",
                        msg_zh=f"下载 {bangumi.official_title} 成功。",
                    )
            else:
                return ResponseModel(
                    status=False,
                    status_code=406,
                    msg_en=f"[Engine] Download {bangumi.official_title} failed.",
                    msg_zh=f"[Engine] 下载 {bangumi.official_title} 失败。",
                )

    @staticmethod
    def __connect_database():
        return Database(engine)


