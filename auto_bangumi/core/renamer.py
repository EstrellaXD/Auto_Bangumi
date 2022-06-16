import logging
import re
from pathlib import PurePath, PureWindowsPath

from conf import settings
from core import DownloadClient
from parser import TitleParser

logger = logging.getLogger(__name__)


class Renamer:
    def __init__(self, download_client: DownloadClient):
        self.client = download_client
        self._renamer = TitleParser()
        self.recent_info = self.client.get_torrent_info()
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)

    def print_result(self):
        logger.info(f"Finished checking {self.torrent_count} files' name.")
        logger.info(f"Renamed {self.rename_count} files.")
        logger.info(f"Finished rename process.")

    def refresh(self):
        self.recent_info = self.client.get_torrent_info()

    def run(self):
        for i in range(0, self.torrent_count):
            info = self.recent_info[i]
            name = info.name
            torrent_hash = info.hash
            path_parts = PurePath(info.content_path).parts \
                if PurePath(info.content_path).name != info.content_path \
                else PureWindowsPath(info.content_path).parts
            path_name = path_parts[-1]
            season = int(re.search(r"\d", path_parts[-2]).group())
            try:
                new_name = self._renamer.download_parser(name, season, settings.method)
                logger.debug(f"Origin name: {path_name}")
                logger.debug(f"New name: {new_name}")
                if path_name != new_name:
                    self.client.rename_torrent_file(torrent_hash, path_name, new_name)
                    self.rename_count += 1
                else:
                    continue
            except:
                logger.warning(f"{path_name} rename failed")
                if settings.remove_bad_torrent:
                    self.client.delete_torrent(torrent_hash)
        self.print_result()


if __name__ == "__main__":
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    client = DownloadClient()
    rename = Renamer(client)
    rename.run()
