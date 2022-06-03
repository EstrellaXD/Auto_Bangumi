import re
import logging
from core.download_client import DownloadClient

from conf import settings

logger = logging.getLogger(__name__)

rules = [
    r"(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
    r"(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
    r"(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)",
    r"(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)",
    r"(.*)第(\d*\.*\d*)话(?:END)?(.*)",
    r"(.*)第(\d*\.*\d*)話(?:END)?(.*)",
    r"(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)",
]


class Renamer:
    def __init__(self, downloadClient: DownloadClient):
        self.client = downloadClient
        self.rules = [re.compile(rule) for rule in rules]

    def rename_normal(self, name):
        for rule in self.rules:
            matchObj = rule.match(name, re.I)
            if matchObj is not None:
                new_name = f"{matchObj.group(1).strip()} E{matchObj.group(2)}{matchObj.group(3)}"
                return new_name

    def rename_pn(self, name):
        n = re.split(r"\[|\]", name)
        file_name = name.replace(f"[{n[1]}]", "")
        for rule in self.rules:
            matchObj = rule.match(file_name, re.I)
            if matchObj is not None:
                new_name = re.sub(
                    r"\[|\]",
                    "",
                    f"{matchObj.group(1).strip()} E{matchObj.group(2)}{n[-1]}",
                )
                return new_name

    def print_result(self, torrent_count, rename_count):
        logger.debug(f"已完成对{torrent_count}个文件的检查")
        logger.debug(f"已对其中{rename_count}个文件进行重命名")
        logger.debug(f"完成")

    def run(self):
        recent_info = self.client.get_torrent_info()
        rename_count = 0
        torrent_count = len(recent_info)
        method_dict = {"pn": self.rename_pn, "normal": self.rename_normal}
        if settings.method not in method_dict:
            logger.error(f"error method")
        else:
            for i in range(0, torrent_count):
                try:
                    info = recent_info[i]
                    name = info.name
                    hash = info.hash
                    path_name = info.content_path.split("/")[-1]
                    new_name = method_dict[settings.method](name)
                    if path_name != new_name:
                        self.client.rename_torrent_file(hash, path_name, new_name)
                        rename_count += 1
                except:
                    logger.warning(f"{name} rename fail")
            self.print_result(torrent_count, rename_count)
