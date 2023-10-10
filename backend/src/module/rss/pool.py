import asyncio
from typing import Callable

from module.models import RSSItem, Torrent
from module.network import RequestContent
from module.conf import settings


async def rss_checker(rss: list[RSSItem], callback: Callable[[list[Torrent]], None]):
    torrent_pool = []
    torrent_name_pool = []
    while 1:
        async with RequestContent() as req:
            for item in rss:
                torrents = await req.get_torrents(item.url)
                for torrent in torrents:
                    if torrent.name not in torrent_name_pool:
                        torrent_pool.append(torrent)
                        torrent_name_pool.append(torrent.name)
            if torrent_pool:
                callback(torrent_pool)
                torrent_pool.clear()
        await asyncio.sleep(settings.rss.interval)

