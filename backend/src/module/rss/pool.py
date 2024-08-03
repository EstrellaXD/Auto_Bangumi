import asyncio
import time

from module.conf import settings
from module.models import RSSItem, Torrent
from module.models.bangumi import Bangumi
from module.network import RequestContent
from module.downloader import DownloadClient
from engine import RSSEngine
from module.database import Database, engine


async def rss_checker(rss_list: list[RSSItem]):
    torrent_pool = []
    torrent_name_pool = []
    while 1:
        async with RequestContent() as req:
            for item in rss_list:
                torrents = await req.get_torrents(item.url)
                for torrent in torrents:
                    if torrent.name not in torrent_name_pool:
                        torrent_pool.append(torrent)
                        torrent_name_pool.append(torrent.name)
            if torrent_pool:
                torrent_pool.clear()
        await asyncio.sleep(settings.rss.interval)



if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # asyncio.run(rss_poller())
