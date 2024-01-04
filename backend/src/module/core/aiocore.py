import asyncio

from module.downloader import DownloadClient
from module.manager import Renamer
from module.conf import settings
from module.rss import RSSEngine
from module.database import Database
from module.models import Bangumi, RSSItem, Torrent



rss_item_pool = []
torrent_pool: list[tuple[Bangumi, list[Torrent]]] = []


class AsyncProgram:
    def __init__(self):
        self.renamer = Renamer()
        self.engine = RSSEngine()
        self.event = asyncio.Event()

    async def run(self):
        self.event.clear()
        task = []
        if settings.bangumi_manage.enable:
            task.append(self.rename_task())
        if settings.rss_parser.enable:
            task.append(self.rss_task())
        await asyncio.gather(*task)

    async def rename_task(self):
        while not self.event.is_set():
            async with DownloadClient() as client:
                await self.check_downloader(client)
                await self.renamer.rename(client)
                await asyncio.sleep(settings.program.rename_time)

    async def rss_task(self):
        while not self.event.is_set():
            await self.engine.rss_poller(process_rss)
            await asyncio.sleep(settings.program.rss_time)


async def rename_task():
    connected = False
    renamer = Renamer()
    async with DownloadClient() as client:
        while not connected:
            connected = await client.auth()
            if not connected:
                await asyncio.sleep(30)
        for bangumi, torrents in torrent_pool:
            client.add_torrent(torrents, bangumi)
        renamer.rename(client)
        await asyncio.sleep(settings.program.rename_time)


async def rss_task():
    # GET RSS FROM DATABASE
    with Database() as db:
        rss_items = db.rss.search_active()
        for rss_item in rss_items:
            rss_item_pool.append(rss_item)
    pass
