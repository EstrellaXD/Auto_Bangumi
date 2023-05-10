import logging
import time

from qbittorrentapi import Client, LoginFailed
from qbittorrentapi.exceptions import Conflict409Error

from module.ab_decorator import qb_connect_failed_wait
from module.downloader.exceptions import ConflictError

logger = logging.getLogger(__name__)


class QbDownloader:
    def __init__(self, host: str, username: str, password: str, ssl: bool):
        self._client: Client = Client(
            host=host,
            username=username,
            password=password,
            VERIFY_WEBUI_CERTIFICATE=ssl,
        )
        self.host = host
        self.username = username

    @qb_connect_failed_wait
    def auth(self):
        while True:
            try:
                self._client.auth_log_in()
                break
            except LoginFailed:
                logger.error(
                    f"Can't login qBittorrent Server {self.host} by {self.username}, retry in {5} seconds."
                )
            time.sleep(5)

    def logout(self):
        self._client.auth_log_out()

    @qb_connect_failed_wait
    def prefs_init(self, prefs):
        return self._client.app_set_preferences(prefs=prefs)

    @qb_connect_failed_wait
    def get_app_prefs(self):
        return self._client.app_preferences()

    def add_category(self, category):
        return self._client.torrents_createCategory(name=category)

    @qb_connect_failed_wait
    def torrents_info(self, status_filter, category):
        return self._client.torrents_info(status_filter, category)

    def torrents_add(self, urls, save_path, category):
        return self._client.torrents_add(
            is_paused=False,
            urls=urls,
            save_path=save_path,
            category=category,
        )

    def torrents_delete(self, hash):
        return self._client.torrents_delete(delete_files=True, torrent_hashes=hash)

    def torrents_rename_file(self, torrent_hash, old_path, new_path) -> bool:
        try:
            self._client.torrents_rename_file(
                torrent_hash=torrent_hash, old_path=old_path, new_path=new_path
            )
            return True
        except Conflict409Error:
            logger.debug(f"Conflict409Error: {old_path} >> {new_path}")
            return False

    def check_rss(self, url, item_path) -> tuple[str | None, bool]:
        items = self._client.rss_items()
        for key, value in items.items():
            rss_url = value.get("url")
            if key == item_path:
                if rss_url != url:
                    return key, False
                return None, True
            else:
                if rss_url == url:
                    return key, True
        return None, False

    def rss_add_feed(self, url, item_path):
        path, added = self.check_rss(url, item_path)
        if path:
            if not added:
                logger.info("RSS Exist, Update URL.")
                self._client.rss_remove_item(path)
                self._client.rss_add_feed(url, item_path)
            else:
                logger.info("RSS Exist.")
        else:
            if added:
                logger.info("RSS Exist.")
            else:
                logger.info("Add new RSS")
                self._client.rss_add_feed(url, item_path)
                logger.info("Successfully added RSS")

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

    def get_torrent_path(self, _hash):
        return self._client.torrents_info(hashes=_hash)[0].save_path

    def set_category(self, _hash, category):
        self._client.torrents_set_category(category, hashes=_hash)

    def check_connection(self):
        return self._client.app_version()

    def remove_rule(self, rule_name):
        self._client.rss_remove_rule(rule_name)
