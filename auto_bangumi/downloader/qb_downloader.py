import logging
import time

from qbittorrentapi import Client, LoginFailed
from qbittorrentapi.exceptions import Conflict409Error

from conf import settings

from downloader.exceptions import ConflictError

logger = logging.getLogger(__name__)


class QbDownloader:
    def __init__(self, host, username, password):
        self._client = Client(
            host=host,
            username=username,
            password=password,
        )
        while True:
            try:
                self._client.auth_log_in()
                break
            except LoginFailed:
                logger.warning(
                    f"Can't log in qBittorrent Server {host} by {username}, retry in {settings.connect_retry_interval}"
                )
            time.sleep(settings.connect_retry_interval)

    def prefs_init(self, prefs):
        return self._client.app_set_preferences(prefs=prefs)

    def torrents_info(self, status_filter, category):
        return self._client.torrents_info(status_filter, category)

    def torrents_add(self, urls, save_path, category):
        return self._client.torrents_add(
            is_paused=settings.add_pause,
            urls=urls,
            save_path=save_path,
            category=category,
        )

    def torrents_delete(self, hash):
        return self._client.torrents_delete(
            delete_files=False,
            torrent_hashes=hash
        )

    def torrents_rename_file(self, torrent_hash, old_path, new_path):
        self._client.torrents_rename_file(torrent_hash=torrent_hash, old_path=old_path, new_path=new_path)

    def rss_add_feed(self, url, item_path):
        try:
            self._client.rss_add_feed(url, item_path)
        except Conflict409Error as e:
            logger.exception(e)
            raise ConflictError()

    def rss_remove_item(self, item_path):
        try:
            self._client.rss_remove_item(item_path)
        except Conflict409Error as e:
            logger.exception(e)
            raise ConflictError()

    def rss_set_rule(self, rule_name, rule_def):
        self._client.rss_set_rule(rule_name, rule_def)
