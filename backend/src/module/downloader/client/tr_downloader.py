import logging
import time
import re

from transmission_rpc import Client, TransmissionError
from transmission_rpc.error import (
    TransmissionConnectError,
    TransmissionAuthError,
)

logger = logging.getLogger(__name__)


class TrDownloader:
    def __init__(self, host: str, username: str, password: str, ssl: bool):
        host, port = self.parse_host(host)
        self._client = self.connect(host, port, username, password)
        self.host = host
        self.username = username
        self.connect(host, port, username, password)

    def parse_host(self, host_str: str):
        regex = re.compile(r'(?:(?:http|https):\/\/)?([\w\d\.-]+:[\d]+)')
        host_str = regex.search(host_str).group(1)
        host, port = host_str.split(":")

        try:
            return host, int(port)
        except ValueError:
            logger.warning("Cannot parse port, use default port 9091")
            return host_str, 9091
        except Exception as e:
            logger.error(f"Unknown error: {e}, use default port 9091")
            return host_str, 9091

    def auth(self):
        try:
            self._client.get_session()
            return True
        except TransmissionError:
            return False

    def logout(self):
        pass

    def connect(self, host: str, port: int, username: str, password: str, retry=3):
        times = 0
        while times < retry:
            try:
                return Client(host=host, port=port, username=username, password=password)
            except TransmissionAuthError:
                logger.error(
                    f"Can't login Transmission Server {self.host} by {self.username}, retry in {5} seconds."
                )
                time.sleep(5)
                times += 1
            except TransmissionConnectError:
                logger.error("Cannot connect to TransmissionServer")
                logger.info("Please check the IP and port in settings")
                time.sleep(10)
                times += 1
            except Exception as e:
                logger.error(f"Unknown error: {e}")
                break
        raise Exception("Cannot connect to TransmissionServer")

    def add_torrent(self, torrent: str, download_dir: str, labels: str):
        res = self._client.add_torrent(torrent=torrent, download_dir=download_dir, labels=labels, paused=False)
        return res.error == 0

    def add_torrents(self, torrent_urls, torrent_files, save_path, category):
        res = True
        for torrent in torrent_urls:
            res = res and self.add_torrent(torrent, save_path, labels=category)

        for torrent in torrent_files:
            res = res and self.add_torrent(torrent, save_path, labels=category)
        return res

    def torrents_delete(self, hashes):
        return self._client.remove_torrent(hashes, delete_data=True)

    def torrents_rename_file(self, torrent_hash, old_path, new_path) -> bool:
        # old path just use to be compatible with download_client.py
        torrent = self._client.get_torrent(torrent_hash)

        try:
            self._client.rename_torrent_path(torrent_hash, location=new_path, name=torrent.name)
            return True
        except TransmissionError:
            logger.debug(f"Error: {torrent.download_dir} >> {new_path}")
            return False

    def move_torrent(self, hashes, new_location):
        self._client.move_torrent_data(hashes, new_location)
