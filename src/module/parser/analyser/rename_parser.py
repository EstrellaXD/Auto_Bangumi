import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DownloadInfo:
    name: str
    season: int
    suffix: str
    file_name: str
    folder_name: str


RULES = [
    r"(.*) - (\d{1,4}|\d{1,4}\.\d{1,2})(?:v\d{1,2})?(?: )?(?:END)?(.*)",
    r"(.*)[\[ E](\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?: )?(?:END)?[\] ](.*)",
    r"(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)",
    r"(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)",
    r"(.*)第(\d*\.*\d*)话(?:END)?(.*)",
    r"(.*)第(\d*\.*\d*)話(?:END)?(.*)",
    r"(.*)E(\d{1,3})(.*)",
]


def rename_init(name, folder_name, season, suffix) -> DownloadInfo:
    n = re.split(r"[\[\]()【】（）]", name)
    suffix = suffix if suffix else n[-1]
    if len(n) > 1:
        file_name = name.replace(f"[{n[1]}]", "")
    else:
        file_name = name
    if season < 10:
        season = f"0{season}"
    return DownloadInfo(name, season, suffix, file_name, folder_name)


def rename_normal(info: DownloadInfo):
    for rule in RULES:
        match_obj = re.match(rule, info.name, re.I)
        if match_obj is not None:
            title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
            new_name = f"{title} S{info.season}E{match_obj.group(2)}{match_obj.group(3)}"
            return new_name


def rename_pn(info: DownloadInfo):
    for rule in RULES:
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


def rename_advance(info: DownloadInfo):
    for rule in RULES:
        match_obj = re.match(rule, info.file_name, re.I)
        if match_obj is not None:
            new_name = re.sub(
                r"[\[\]]",
                "",
                f"{info.folder_name} S{info.season}E{match_obj.group(2)}{info.suffix}",
            )
            return new_name


def rename_no_season_pn(info: DownloadInfo):
    for rule in RULES:
        match_obj = re.match(rule, info.file_name, re.I)
        if match_obj is not None:
            title = match_obj.group(1).strip()
            new_name = re.sub(
                r"[\[\]]",
                "",
                f"{title} E{match_obj.group(2)}{info.suffix}",
            )
            return new_name


def rename_none(info: DownloadInfo):
    return info.name


METHODS = {
    "normal": rename_normal,
    "pn": rename_pn,
    "advance": rename_advance,
    "no_season_pn": rename_no_season_pn,
    "none": rename_none
}


def torrent_parser(
        file_name: str,
        folder_name: str,
        season: int,
        suffix: str,
        method: str = "pn",
):
    info = rename_init(file_name, folder_name, season, suffix)
    return METHODS[method.lower()](info)


if __name__ == "__main__":
    name = "[Lilith-Raws] Tate no Yuusha no Nariagari S02 - 02 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    new_name = torrent_parser(name, "异世界舅舅（2022）", 2, ".mp4", "advance")
    print(new_name)
