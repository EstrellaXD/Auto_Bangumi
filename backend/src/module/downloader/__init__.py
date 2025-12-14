import logging

from models.config import Downloader as DownloaderConfig
from conf.config import get_config_by_key

from .download_client import DownloadClient
from .download_queue import DownloadQueue, download_queue

logger = logging.getLogger(__name__)

Client: DownloadClient= DownloadClient(DownloaderConfig())  # type: ignore


def init(config: DownloaderConfig|None= None) -> bool:
    if config is None:
        config = get_config_by_key("downloader", DownloaderConfig)
    global Client
    try:
        Client = DownloadClient(config)
    except Exception as e:
        logger.error(f"Failed to initialize DownloadClient: {e}")
        return False
    return True


__all__ = [
    "DownloadClient",
    "DownloadQueue",
    "Client",
    "download_queue",
]
