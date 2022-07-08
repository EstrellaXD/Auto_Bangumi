import re
import logging
from os import path

# from .raw_parser import RawParser

logger = logging.getLogger(__name__)


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

    def rename_normal(self, info_dict):
        name = info_dict["name"]
        season = info_dict["season"]
        for rule in self.rules:
            match_obj = re.match(rule, name, re.I)
            if match_obj is not None:
                title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
                new_name = f"{title} S{season}E{match_obj.group(2)}{match_obj.group(3)}"
                return new_name

    def rename_pn(self, info_dict):
        name = info_dict["name"]
        season = info_dict["season"]
        suffix = info_dict["suffix"]
        n = re.split(r"[\[\]()【】（）]", name)
        file_name = name.replace(f"[{n[1]}]", "")
        if season < 10:
            season = f"0{season}"
        for rule in self.rules:
            match_obj = re.match(rule, file_name, re.I)
            if match_obj is not None:
                title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
                title = title if title != "" else info_dict.get("folder_name")
                new_name = re.sub(
                    r"[\[\]]",
                    "",
                    f"{title} S{season}E{match_obj.group(2)}{suffix}",
                )
                return new_name

    def rename_advance(self, info_dict):
        name = info_dict["name"]
        folder_name = info_dict["folder_name"]
        suffix = info_dict["suffix"]
        season = info_dict["season"]
        n = re.split(r"[\[\]()【】（）]", name)
        file_name = name.replace(f"[{n[1]}]", "")
        if season < 10:
            season = f"0{season}"
        for rule in self.rules:
            match_obj = re.match(rule, file_name, re.I)
            if match_obj is not None:
                new_name = re.sub(
                    r"[\[\]]",
                    "",
                    f"{folder_name} S{season}E{match_obj.group(2)}{suffix}",
                )
                return new_name

    def rename_no_season_pn(self, info_dict):
        name = info_dict["name"]
        suffix = info_dict["suffix"]
        n = re.split(r"[\[\]()【】（）]", name)
        file_name = name.replace(f"[{n[1]}]", "")
        for rule in self.rules:
            match_obj = re.match(rule, file_name, re.I)
            if match_obj is not None:
                title = match_obj.group(1).strip()
                new_name = re.sub(
                    r"[\[\]]",
                    "",
                    f"{title} E{match_obj.group(2)}{suffix}",
                )
                return new_name

    @staticmethod
    def rename_none(self, info_dict):
        return info_dict["name"]

    def download_rename(self, name, folder_name, season,suffix, method):
        info_dict = {
            "name": name,
            "folder_name": folder_name,
            "season": season,
            "suffix": suffix
        }
        method_dict = {
            "normal": self.rename_normal,
            "pn": self.rename_pn,
            "advance": self.rename_advance,
            "no_season_pn": self.rename_no_season_pn,
            "none": self.rename_none
        }
        logger.debug(f"Name: {folder_name}, File type: {path.splitext(name)[-1]}, Season {season}")
        return method_dict[method](info_dict)


if __name__ == "__main__":
    name = "[Isekai Meikyuu de Harem wo][01][BIG5][1080P][AT-X].mp4"
    rename = DownloadParser()
    new_name = rename.download_rename(name, "Made abyess", 1, ".mp4", "pn")
    print(new_name)