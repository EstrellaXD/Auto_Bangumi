import logging

from module.conf import settings
from module.downloader import DownloadClient
from module.network import RequestContent

logger = logging.getLogger(__name__)


def check_status() -> bool:
    if settings.rss_parser.token in ["", "token"]:
        logger.warning("Please set RSS token")
        return False
    if check_downloader():
        logger.debug("All check passed")
        return True
    return False


def check_downloader():
    with DownloadClient() as client:
        if client.authed:
            logger.debug("Downloader is running")
            return True
        else:
            logger.warning("Can't connect to downloader")
            return False


def check_rss():
    rss_link = settings.rss_link()
    with RequestContent() as req:
        try:
            torrents = req.get_torrents(rss_link)
        except Exception as e:
            logger.warning("Failed to get torrents from RSS")
            logger.warning(e)
            return False
        if not torrents:
            logger.warning("No torrents in RSS")
            logger.warning("Please check your RSS link")
            return False
        else:
            logger.debug("RSS is running")
            return True
