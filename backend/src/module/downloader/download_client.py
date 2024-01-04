import logging
import asyncio

from module.conf import settings
from module.models import Bangumi, Torrent
from module.network import RequestContent

from .path import TorrentPath

logger = logging.getLogger(__name__)


def getClient():
    # TODO 多下载器支持
    if settings.downloader.type == "qbittorrent":
        from .client.qb_downloader import QbDownloader

        return QbDownloader
    elif type == "transmission":
        from .client.tr_downloader import TrDownloader

        return TrDownloader
    else:
        logger.error(f"[Downloader] Unsupported downloader type: {type}")
        raise Exception(f"Unsupported downloader type: {type}")


class DownloadClient(getClient(), TorrentPath):
    def __init__(self):
        super().__init__(
            host=settings.downloader.host,
            username=settings.downloader.username,
            password=settings.downloader.password,
            ssl=settings.downloader.ssl,
        )

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

    async def add_torrents(self, torrents: list[Torrent], bangumi: Bangumi) -> bool:
        if not bangumi.save_path:
            bangumi.save_path = self._gen_save_path(bangumi)
        async with RequestContent() as req:
            if "magnet" in torrents[0].url:
                torrent_url = [t.url for t in torrents]
                torrent_file = None
            else:
                tasks = []
                for t in torrents:
                    tasks.append(req.get_content(t.url))
                torrent_file = asyncio.gather(*tasks)
                torrent_url = None
        result = await self.add(
            torrent_urls=torrent_url,
            torrent_files=torrent_file,
            save_path=bangumi.save_path,
            category="Bangumi",
        )
        if result:
            logger.debug(f"[Downloader] Add torrent: {bangumi.official_title}")
            return True
        else:
            logger.debug(f"[Downloader] Torrent added before: {bangumi.official_title}")
            return False

    async def move_torrent(self, hashes, location):
        await self.move(hashes=hashes, new_location=location)

    async def set_category(self, hashes, category):
        await self.set_category(hashes, category)
