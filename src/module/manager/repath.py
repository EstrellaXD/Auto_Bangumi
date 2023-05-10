import logging

from module.downloader import DownloadClient
from module.conf import settings
from module.models import BangumiData

logger = logging.getLogger(__name__)


def __gen_path(data: BangumiData):
    download_path = settings.downloader.path
    if ":\\" in download_path:
        import ntpath as path
    else:
        import os.path as path
    folder = f"{data.official_title}({data.year})" if data.year else data.official_title
    path = path.join(download_path, folder, f"Season {data.season}")
    return path


def match_torrents_list(title_raw: str) -> list:
    with DownloadClient() as client:
        torrents = client.get_torrent_info()
    return [torrent.hash for torrent in torrents if title_raw in torrent.name]


def set_new_path(data: BangumiData):
    with DownloadClient() as client:
        # set download rule
        client.set_rule(data)
        # set torrent path
        match_list = match_torrents_list(data.title_raw)
        path = __gen_path(data)
        client.move_torrent(match_list, path)

