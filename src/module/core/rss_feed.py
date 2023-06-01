import logging

from module.downloader import DownloadClient
from module.conf import settings

logger = logging.getLogger(__name__)


def add_rss_feed():
    with DownloadClient() as client:
        # Check Feed if exists
        add = True
        remove = False
        feeds = client.get_rss_feed()
        for item_path, value in feeds.items():
            if value.url == settings.rss_link:
                add = False
                break
            elif item_path == "Mikan_RSS":
                remove = True
        if remove:
            client.remove_rss_feed("Mikan_RSS")
            logger.info("Remove Old RSS Feed: Mikan_RSS")
        # Add Feed
        if add:
            client.add_rss_feed(settings.rss_link)
            logger.info(f"Add RSS Feed: {settings.rss_link}")


if __name__ == "__main__":
    from module.conf import setup_logger

    setup_logger()
    add_rss_feed()
