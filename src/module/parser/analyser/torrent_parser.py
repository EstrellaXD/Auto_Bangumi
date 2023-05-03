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
    r"(.*)\[(?:第)?(\d*\.*\d*)[话集話](?:END)?\](.*)",
    r"(.*)第(\d*\.*\d*)[话話集](?:END)?(.*)",
    r"(.*)EP?(\d{1,4})(.*)",
]

SUBTITLE_LANG = {
    "zh-tw": ["TC", "CHT", "繁", "zh-tw"],
    "zh": ["SC", "CHS", "简", "zh"],
}


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


def rename_subtitle(info: DownloadInfo):
    subtitle_lang = "zh"
    break_flag = False
    for key, value in SUBTITLE_LANG.items():
        for lang in value:
            if lang in info.name:
                subtitle_lang = key
                break_flag = True
                break
        if break_flag:
            break
    for rule in RULES:
        match_obj = re.match(rule, info.file_name, re.I)
        if match_obj is not None:
            title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
            title = title if title != "" else info.folder_name
            new_name = re.sub(
                r"[\[\]]",
                "",
                f"{title} S{info.season}E{match_obj.group(2)}.{subtitle_lang}{info.suffix}",
            )
            return new_name


def rename_subtitle_advance(info: DownloadInfo):
    subtitle_lang = "zh"
    break_flag = False
    for key, value in SUBTITLE_LANG.items():
        for lang in value:
            if lang in info.name:
                subtitle_lang = key
                break_flag = True
                break
        if break_flag:
            break
    for rule in RULES:
        match_obj = re.match(rule, info.file_name, re.I)
        if match_obj is not None:
            new_name = re.sub(
                r"[\[\]]",
                "",
                f"{info.folder_name} S{info.season}E{match_obj.group(2)}.{subtitle_lang}{info.suffix}",
            )
            return new_name


METHODS = {
    "normal": rename_normal,
    "pn": rename_pn,
    "advance": rename_advance,
    "no_season_pn": rename_no_season_pn,
    "none": rename_none,
    "subtitle_pn": rename_subtitle,
    "subtitle_advance": rename_subtitle_advance,
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

