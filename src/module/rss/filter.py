import logging

from module.database import BangumiDatabase
from module.downloader import DownloadClient
from module.network import RequestContent
from module.conf import settings
from module.models import BangumiData

logger = logging.getLogger(__name__)


def matched(torrent_title: str):
    with BangumiDatabase() as db:
        return db.match_torrent(torrent_title)


def save_path(data: BangumiData):
    folder = (
        f"{data.official_title}({data.year})" if data.year else f"{data.official_title}"
    )
    season = f"Season {data.season}"
    return path.join(
        settings.downloader.path,
        folder,
        season,
    )


def add_download(data: BangumiData, torrent: TorrentInfo):
    torrent = {
        "url": torrent.url,
        "save_path": save_path(data),
    }
    with DownloadClient() as client:
        client.add_torrent(torrent)
    with TorrentDatabase() as db:
        db.add_torrent(torrent)


def downloaded(torrent: TorrentInfo):
    with TorrentDatabase() as db:
        return db.if_downloaded(torrent)


def get_downloads(rss_link: str):
    with RequestContent() as req:
        torrents = req.get_torrents(rss_link)
    for torrent in torrents:
        if not downloaded(torrent):
            data = matched(torrent.title)
            if data:
                add_download(data, torrent)
                logger.info(f"Add {torrent.title} to download list")
            else:
                logger.debug(f"{torrent.title} not matched")
        else:
            logger.debug(f"{torrent.title} already downloaded")
