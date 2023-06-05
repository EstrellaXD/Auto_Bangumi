import logging
import time

from qbittorrentapi import Client, LoginFailed
from qbittorrentapi.exceptions import (
    Conflict409Error,
    Forbidden403Error,
    APIConnectionError,
)

from module.ab_decorator import qb_connect_failed_wait

logger = logging.getLogger(__name__)


class QbDownloader:
    def __init__(self, host: str, username: str, password: str, ssl: bool):
        self._client: Client = Client(
            host=host,
            username=username,
            password=password,
            VERIFY_WEBUI_CERTIFICATE=ssl,
            DISABLE_LOGGING_DEBUG_OUTPUT=True,
            REQUESTS_ARGS={"timeout": (3.1, 10)},
        )
        self.host = host
        self.username = username

    def auth(self, retry=3):
        times = 0
        while times < retry:
            try:
                self._client.auth_log_in()
                return True
            except LoginFailed:
                logger.error(
                    f"Can't login qBittorrent Server {self.host} by {self.username}, retry in {5} seconds."
                )
                time.sleep(5)
                times += 1
            except Forbidden403Error:
                logger.error(f"Login refused by qBittorrent Server")
                logger.info(f"Please release the IP in qBittorrent Server")
                break
            except APIConnectionError:
                logger.error(f"Cannot connect to qBittorrent Server")
                logger.info(f"Please check the IP and port in WebUI settings")
                time.sleep(10)
                times += 1
            except Exception as e:
                logger.error(f"Unknown error: {e}")
                break
        return False

    def logout(self):
        self._client.auth_log_out()

    def check_host(self):
        try:
            self._client.app_version()
            return True
        except APIConnectionError:
            return False

    def check_rss(self, rss_link: str):
        pass

    @qb_connect_failed_wait
    def prefs_init(self, prefs):
        return self._client.app_set_preferences(prefs=prefs)

    @qb_connect_failed_wait
    def get_app_prefs(self):
        return self._client.app_preferences()

    def add_category(self, category):
        return self._client.torrents_createCategory(name=category)

    @qb_connect_failed_wait
    def torrents_info(self, status_filter, category, tag=None):
        return self._client.torrents_info(status_filter=status_filter, category=category, tag=tag)

    def torrents_add(self, urls, save_path, category, torrent_files=None):
        resp = self._client.torrents_add(
            is_paused=False,
            urls=urls,
            torrent_files=torrent_files,
            save_path=save_path,
            category=category,
            use_auto_torrent_management=False
        )
        return resp == "Ok."

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

    def rss_add_feed(self, url, item_path):
        try:
            self._client.rss_add_feed(url, item_path)
        except Conflict409Error:
            logger.warning(f"[Downloader] RSS feed {url} already exists")

    def rss_remove_item(self, item_path):
        try:
            self._client.rss_remove_item(item_path)
        except Conflict409Error:
            logger.warning(f"[Downloader] RSS item {item_path} does not exist")

    def rss_get_feeds(self):
        return self._client.rss_items()

    def rss_set_rule(self, rule_name, rule_def):
        self._client.rss_set_rule(rule_name, rule_def)

    def move_torrent(self, hashes, new_location):
        self._client.torrents_set_location(new_location, hashes)

    def get_download_rule(self):
        return self._client.rss_rules()

    def get_torrent_path(self, _hash):
        return self._client.torrents_info(hashes=_hash)[0].save_path

    def set_category(self, _hash, category):
        try:
            self._client.torrents_set_category(category, hashes=_hash)
        except Conflict409Error:
            logger.warning(f"[Downloader] Category {category} does not exist")
            self.add_category(category)
            self._client.torrents_set_category(category, hashes=_hash)

    def check_connection(self):
        return self._client.app_version()

    def remove_rule(self, rule_name):
        self._client.rss_remove_rule(rule_name)

    def add_tag(self, _hash, tag):
        self._client.torrents_add_tags(tags=tag, hashes=_hash)
