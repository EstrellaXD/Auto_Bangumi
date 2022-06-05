import re
import logging
from pathlib import PurePath

from conf import settings
from core.download_client import DownloadClient

logger = logging.getLogger(__name__)



class Renamer:
    def __init__(self, downloadClient: DownloadClient):
        self.client = downloadClient
        self.rules = [
                        r"(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
                        r"(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
                        r"(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)",
                        r"(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)",
                        r"(.*)第(\d*\.*\d*)话(?:END)?(.*)",
                        r"(.*)第(\d*\.*\d*)話(?:END)?(.*)",
                        r"(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)",
                    ]

    def rename_normal(self, name):
        for rule in self.rules:
            matchObj = re.match(rule, name, re.I)
            if matchObj is not None:
                new_name = f"{matchObj.group(1).strip()} E{matchObj.group(2)}{matchObj.group(3)}"
                return new_name

    def rename_pn(self, name):
        n = re.split(r"\[|\]", name)
        file_name = name.replace(f"[{n[1]}]", "")
        for rule in self.rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                new_name = re.sub(
                    r"\[|\]",
                    "",
                    f"{matchObj.group(1).strip()} E{matchObj.group(2)}{n[-1]}",
                )
                return new_name

    def print_result(self, torrent_count, rename_count):
        logger.info(f"Finished checking {torrent_count} file's name.")
        logger.info(f"Renamed {rename_count} files.")
        logger.info(f"Finished rename process.")

    def run(self):
        recent_info = self.client.get_torrent_info()
        rename_count = 0
        torrent_count = len(recent_info)
        method_dict = {"pn": self.rename_pn, "normal": self.rename_normal}
        if settings.method not in method_dict:
            logger.error(f"error method")
        else:
            for i in range(0, torrent_count):
                info = recent_info[i]
                try:
                    name = info.name
                    hash = info.hash
                    path_name = PurePath(info.content_path).name
                    new_name = method_dict[settings.method](name)
                    if path_name != new_name:
                        self.client.rename_torrent_file(hash, path_name, new_name)
                        rename_count += 1
                except:
                    logger.warning(f"{info.name} rename failed")
                    if settings.remove_bad_torrent:
                        self.client.delete_torrent(info.hash)
            self.print_result(torrent_count, rename_count)


if __name__ == "__main__":
    rename = Renamer()
    rename.rename_pn("[Lilith-Raws] Shokei Shoujo no Virgin Road - 02 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]")