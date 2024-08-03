import asyncio
import logging

from module.conf import settings
from module.downloader.client import Downloader
from module.models import Bangumi, Torrent
from module.network import RequestContent

from .path import TorrentPath

logger = logging.getLogger(__name__)


class DownloadClient(Downloader):
    def __init__(self):
        super().__init__(
            host=settings.downloader.host_,
            username=settings.downloader.username_,
            password=settings.downloader.password_,
            ssl=settings.downloader.ssl,
        ),
        self._path_parser = TorrentPath

    async def get_torrent_info(
        self, category="Bangumi", status_filter="completed", tag=None
    ):
        return await self.torrents_info(
            status_filter=status_filter, category=category, tag=tag
        )

    async def rename_torrent_file(self, _hash, old_path, new_path) -> bool:
        logger.info(f"{old_path} >> {new_path}")
        return await self.rename(
            torrent_hash=_hash, old_path=old_path, new_path=new_path
        )

    async def delete_torrent(self, hashes):
        resp = await self.delete(hashes)
        logger.info("[Downloader] Remove torrents.")
        return resp

    async def add_torrent(self,torrent:Torrent,bangumi)->bool:
        if not bangumi.save_path:
            bangumi.save_path = self._path_parser.gen_save_path(bangumi)
        if "magnet" in torrent.url:
            torrent_url = torrent.url
            torrent_file = None
        else:
            async with RequestContent() as req:
                # tasks = [req.get_content(t.url) for t in torrents]
                # torrent_file = await asyncio.gather(*tasks,return_exceptions=True)
                torrent_file = await req.get_content(torrent.url)
                torrent_url = None

        result = await self.add(
            torrent_urls=torrent_url,
            torrent_files=torrent_file,
            save_path=bangumi.save_path,
            category="Bangumi",
        )
        if result:
            logger.debug(f"[Downloader] Add torrent: {torrent.name}")
            return True
        else:
            logger.debug(f"[Downloader] Torrent added failed: {torrent.name}")
        return False

    async def add_torrents(self, torrents: list[Torrent], bangumi: Bangumi) -> list[bool|BaseException]:
        tasks = []
        if isinstance(torrents,Torrent):
            torrents = [torrents]
        for torrent in torrents:
            tasks.append( self.add_torrent(torrent,bangumi))

        result = await asyncio.gather(*tasks,return_exceptions=True)
        return result

        # if not bangumi.save_path:
        #     bangumi.save_path = self._path_parser.gen_save_path(bangumi)
        #     print("test",bangumi)
        # if "magnet" in torrents[0].url:
        #     torrent_url = [t.url for t in torrents]
        #     torrent_file = None
        # else:
        #     async with RequestContent() as req:
        #         tasks = [req.get_content(t.url) for t in torrents]
        #         torrent_file = await asyncio.gather(*tasks,return_exceptions=True)
        #         torrent_url = None
        # result = await self.add(
        #     torrent_urls=torrent_url,
        #     torrent_files=torrent_file,
        #     save_path=bangumi.save_path,
        #     category="Bangumi",
        # )
        # if result:
        #     logger.debug(f"[Downloader] Add torrent: {bangumi.official_title}")
        #     return True
        # else:
        #     logger.debug(f"[Downloader] Torrent added before: {bangumi.official_title}")
        #     return False

    async def move_torrent(self, hashes, location):
        await self.move(hashes=hashes, new_location=location)

    async def set_category(self, hashes, category):
        await self.set_category(hashes, category)
