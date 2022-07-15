import logging
import time

from qbittorrentapi import Client, LoginFailed
from qbittorrentapi.exceptions import Conflict409Error

from conf import settings
from ab_decorator import qb_connect_failed_wait

from downloader.exceptions import ConflictError

logger = logging.getLogger(__name__)


class QbDownloader:
    @qb_connect_failed_wait
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
                logger.debug(
                    f"Can't login qBittorrent Server {host} by {username}, retry in {settings.connect_retry_interval}"
                )
            time.sleep(settings.connect_retry_interval)

    @qb_connect_failed_wait
    def prefs_init(self, prefs):
        return self._client.app_set_preferences(prefs=prefs)

    @qb_connect_failed_wait
    def get_app_prefs(self):
        return self._client.app_preferences()

    @qb_connect_failed_wait
    def torrents_info(self, status_filter, category):
        return self._client.torrents_info(status_filter, category)

    def torrents_add(self, urls, save_path, category):
        return self._client.torrents_add(
            is_paused=settings.dev_debug,
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

    def get_rss_info(self):
        item = self._client.rss_items().get("Mikan_RSS")
        if item is not None:
            return item.url
        else:
            return None

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
            logger.debug(e)
            logger.info("Add new RSS")
            raise ConflictError()

    def rss_set_rule(self, rule_name, rule_def):
        self._client.rss_set_rule(rule_name, rule_def)

    def move_torrent(self, hashes, new_location):
        self._client.torrents_set_location(new_location, hashes)

    def get_download_rule(self):
        return self._client.rss_rules()

    def get_torrent_path(self, hash):
        return self._client.torrents_info(hashes=hash)[0].save_path


if __name__ == "__main__":
    try:
        from conf.const_dev import DEV_SETTINGS
    except ModuleNotFoundError:
        logger.debug("Please copy `const_dev.py` to `const_dev.py` to use custom settings")
    settings.init(DEV_SETTINGS)
    client = QbDownloader(settings.host_ip, settings.user_name, settings.password)
    path = client.get_torrent_path("39adad0d0c82ebb3971810a7592e03138b7345d2")
    print(path)
