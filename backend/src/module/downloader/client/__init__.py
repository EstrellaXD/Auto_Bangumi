import logging

from module.conf import settings
from module.downloader.client.qb_downloader import QbDownloader
from module.downloader.client.tr_downloader import TrDownloader

logger = logging.getLogger(__name__)

downloader_type_dict = {
    "qbittorrent": QbDownloader,
    "transmission": TrDownloader,
}

download_client = downloader_type_dict.get(settings.downloader.type, None)
if download_client is None:
    logger.error(f"[Downloader] Unsupported downloader type: {type}")
    raise Exception(f"Unsupported downloader type: {type}")

Downloader = download_client

__all__ = ["Downloader"]
