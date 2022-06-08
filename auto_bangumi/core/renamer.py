import logging
from pathlib import PurePath, PureWindowsPath

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
        logger.info(f"Finished checking {self.torrent_count} files' name.")
        logger.info(f"Renamed {self.rename_count} files.")
        logger.info(f"Finished rename process.")

    def run(self):
        method_dict = {"pn": self._renamer.rename_pn, "normal": self._renamer.rename_normal}
        if settings.method not in method_dict:
            logger.error(f"Error method")
        else:
            for i in range(0, self.torrent_count):
                info = self.recent_info[i]
                name = info.name
                hash = info.hash
                path_name = PurePath(info.content_path).name \
                    if PurePath(info.content_path).name != info.content_path \
                    else PureWindowsPath(info.content_path).name
                try:
                    new_name = method_dict[settings.method](name)
                    logger.debug(f"Origin name: {path_name}")
                    logger.debug(f"New name: {new_name}")
                    if path_name != new_name:
                        self.client.rename_torrent_file(hash, path_name, new_name)
                        self.rename_count += 1
                    else:
                        continue
                except:
                    logger.warning(f"{path_name} rename failed")
                    if settings.remove_bad_torrent:
                        self.client.delete_torrent(hash)
            self.print_result()


if __name__ == "__main__":
    from const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    client = DownloadClient()
    rename = Renamer(client)
    rename.run()
