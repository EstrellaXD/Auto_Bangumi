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

    async def check_downloader(self, client: DownloadClient):
        while 1:
            connected = await client.auth()
            if not connected:
                await asyncio.sleep(30)
            else:
                break

    async def rename_task(self):
        while 1:
            async with DownloadClient() as client:
                await self.check_downloader(client)
                self.renamer.rename(client)
                await asyncio.sleep(settings.program.rename_time)

    async def rss_task(self, engine: RSSEngine):
        while True:
            for rss_item in rss_item_pool:
                torrents = engine.get_rss_torrents(rss_item.id)
                if torrents:
                    torrent_pool.append((rss_item, torrents))
            await asyncio.sleep(settings.program.rss_time)

    async def main_tasks(self):
        async with DownloadClient() as client:
            await self.check_downloader(client)
            await asyncio.gather(
                self.rename_task(client),
                self.rss_task(engine, client)
            )


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