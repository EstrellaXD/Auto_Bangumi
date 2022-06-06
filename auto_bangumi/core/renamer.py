import re
import logging
from pathlib import PurePath

from conf import settings
from core.download_client import DownloadClient
from bangumi_parser.analyser.download_parser import EPParser

logger = logging.getLogger(__name__)


class Renamer:
    def __init__(self, downloadClient: DownloadClient):
        self.client = downloadClient
        self._renamer = EPParser()
        self.recent_info = self.client.get_torrent_info()
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)

    def print_result(self):
        logger.info(f"Finished checking {self.torrent_count} file's name.")
        logger.info(f"Renamed {self.rename_count} files.")
        logger.info(f"Finished rename process.")

    def run(self):
        method_dict = {"pn": self._renamer.rename_pn, "normal": self._renamer.rename_normal}
        if settings.method not in method_dict:
            logger.error(f"error method")
        else:
            for i in range(0, self.torrent_count):
                info = self.recent_info[i]
                try:
                    name = info.name
                    hash = info.hash
                    path_name = PurePath(info.content_path).name
                    new_name = method_dict[settings.method](name)
                    if path_name != new_name:
                        self.client.rename_torrent_file(hash, path_name, new_name)
                        self.rename_count += 1
                except:
                    logger.warning(f"{info.name} rename failed")
                    if settings.remove_bad_torrent:
                        self.client.delete_torrent(info.hash)
            self.print_result()


if __name__ == "__main__":
    client = DownloadClient()
    rename = Renamer(client)
