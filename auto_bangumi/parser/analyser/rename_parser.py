import dataclasses
import re
import logging
from os import path
from dataclasses import dataclass

# from .raw_parser import RawParser

logger = logging.getLogger(__name__)


@dataclass
class DownloadInfo:
    name: str
    season: int
    suffix: str
    file_name: str
    folder_name: str


class DownloadParser:
    def __init__(self):
        self.rules = [
            r"(.*) - (\d{1,4}|\d{1,4}\.\d{1,2})(?:v\d{1,2})?(?: )?(?:END)?(.*)",
            r"(.*)[\[ E](\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?: )?(?:END)?[\] ](.*)",
            r"(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)",
            r"(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)",
            r"(.*)第(\d*\.*\d*)话(?:END)?(.*)",
            r"(.*)第(\d*\.*\d*)話(?:END)?(.*)",
        ]

    @staticmethod
    def rename_init(name, folder_name, season, suffix) -> DownloadInfo:
        n = re.split(r"[\[\]()【】（）]", name)
        suffix = suffix if suffix is not None else n[-1]
        file_name = name.replace(f"[{n[1]}]", "")
        if season < 10:
            season = f"0{season}"
        return DownloadInfo(name, season, suffix, file_name, folder_name)

    def rename_normal(self, info: DownloadInfo):
        for rule in self.rules:
            match_obj = re.match(rule, name, re.I)
            if match_obj is not None:
                title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
                new_name = f"{title} S{info.season}E{match_obj.group(2)}{match_obj.group(3)}"
                return new_name

    def rename_pn(self, info: DownloadInfo):
        for rule in self.rules:
            match_obj = re.match(rule, info.file_name, re.I)
            if match_obj is not None:
                title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
                title = title if title != "" else info.folder_name
                new_name = re.sub(
                    r"[\[\]]",
                    "",
                    f"{title} S{info.season}E{match_obj.group(2)}{info.suffix}",
                )
                return new_name

    def rename_advance(self, info: DownloadInfo):
        for rule in self.rules:
            match_obj = re.match(rule, info.file_name, re.I)
            if match_obj is not None:
                new_name = re.sub(
                    r"[\[\]]",
                    "",
                    f"{info.folder_name} S{info.season}E{match_obj.group(2)}{info.suffix}",
                )
                return new_name

    def rename_no_season_pn(self, info: DownloadInfo):
        for rule in self.rules:
            match_obj = re.match(rule, info.file_name, re.I)
            if match_obj is not None:
                title = match_obj.group(1).strip()
                new_name = re.sub(
                    r"[\[\]]",
                    "",
                    f"{title} E{match_obj.group(2)}{info.suffix}",
                )
                return new_name

    @staticmethod
    def rename_none(info: DownloadInfo):
        return info.name

    def download_rename(self, name, folder_name, season, suffix, method):
        rename_info = self.rename_init(name, folder_name, season, suffix)
        method_dict = {
            "normal": self.rename_normal,
            "pn": self.rename_pn,
            "advance": self.rename_advance,
            "no_season_pn": self.rename_no_season_pn,
            "none": self.rename_none
        }
        logger.debug(f"Name: {folder_name}, File type: {path.splitext(name)[-1]}, Season {season}")
        return method_dict[method.lower()](rename_info)


if __name__ == "__main__":
    name = "[sub][Isekai Meikyuu de Harem wo][01][BIG5][1080P][AT-X].mp4"
    rename = DownloadParser()
    new_name = rename.download_rename(name, "Made abyess", 1, ".mp4", "pn")
    print(new_name)
