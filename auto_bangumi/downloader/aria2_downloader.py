import logging
import time

from aria2p import Client, ClientException, API


from conf import settings

from downloader.exceptions import ConflictError

logger = logging.getLogger(__name__)


class QbDownloader:
    def __init__(self, host, username, password):
        while True:
            try:
                self._client = API(
                    Client(
                        host=host,
                        port=6800,
                        secret=password
                    )
                )
                break
            except ClientException:
                logger.warning(
                    f"Can't login Aria2 Server {host} by {username}, retry in {settings.connect_retry_interval}"
                )
            time.sleep(settings.connect_retry_interval)

    def torrents_add(self, urls, save_path, category):
        return self._client.add_torrent(
            is_paused=settings.dev_debug,
            torrent_file_path=urls,
            save_path=save_path,
            category=category,
        )