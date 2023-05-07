import re
import logging
from dataclasses import dataclass
import os.path as unix_path
import ntpath as win_path

from module.models.torrent import EpisodeFile, SubtitleFile

logger = logging.getLogger(__name__)

PLATFORM = "Unix"

@dataclass
class DownloadInfo:
    name: str
    season: int
    suffix: str
    file_name: str
    folder_name: str


RULES = [
    r"(.*) - (\d{1,4}|\d{1,4}\.\d{1,2})(?:v\d{1,2})?(?: )?(?:END)?(.*)",
    r"(.*)[\[\ E](\d{1,4}|\d{1,4}\.\d{1,2})(?:v\d{1,2})?(?: )?(?:END)?[\]\ ](.*)",
    r"(.*)\[(?:第)?(\d*\.*\d*)[话集話](?:END)?\](.*)",
    r"(.*)第(\d*\.*\d*)[话話集](?:END)?(.*)",
    r"(.*)(?:S\d{2})?EP?(\d+)(.*)",
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


def split_path(torrent_path: str) -> str:
    if PLATFORM == "Windows":
        return win_path.split(torrent_path)[-1]
    else:
        return unix_path.split(torrent_path)[-1]


def get_group(group_and_title) -> tuple[str | None, str]:
    n = re.split(r"[\[\]()【】（）]", group_and_title)
    while "" in n:
        n.remove("")
    if len(n) > 1:
        return n[0], n[1]
    else:
        return None, n[0]


def get_season_and_title(season_and_title) -> tuple[str, int]:
    title = re.sub(r"([Ss]|Season )\d{1,3}", "", season_and_title).strip()
    try:
        season = re.search(r"([Ss]|Season )(\d{1,3})", season_and_title, re.I).group(2)
    except AttributeError:
        season = 1
    return title, int(season)


def get_subtitle_lang(subtitle_name: str) -> str:
    for key, value in SUBTITLE_LANG.items():
        for v in value:
            if v in subtitle_name:
                return key


def parse_torrent(torrent_path: str, season: int | None = None, file_type: str = "media") -> EpisodeFile | SubtitleFile:
    media_path = split_path(torrent_path)
    for rule in RULES:
        match_obj = re.match(rule, media_path, re.I)
        if match_obj is not None:
            group, title = get_group(match_obj.group(1))
            if season is None:
                title, season = get_season_and_title(title)
            else:
                title, _ = get_season_and_title(title)
            episode = int(match_obj.group(2))
            suffix = unix_path.splitext(torrent_path)[-1]
            if file_type == "media":
                return EpisodeFile(
                    group=group,
                    title=title,
                    season=season,
                    episode=episode,
                    suffix=suffix
                )
            elif file_type == "subtitle":
                language = get_subtitle_lang(media_path)
                return SubtitleFile(
                    group=group,
                    title=title,
                    season=season,
                    language=language,
                    episode=episode,
                    suffix=suffix
                )


def rename_normal(info: DownloadInfo):
    for rule in RULES:
        match_obj = re.match(rule, info.name, re.I)
        if match_obj is not None:
            episode = match_obj.group(2)
            title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
            new_name = f"{title} S{info.season}E{episode}{match_obj.group(3)}"
            return new_name


def rename_pn(info: DownloadInfo):
    for rule in RULES:
        match_obj = re.match(rule, info.file_name, re.I)
        if match_obj is not None:
            title = re.sub(r"([Ss]|Season )\d{1,3}", "", match_obj.group(1)).strip()
            title = title if title != "" else info.folder_name
            episode = match_obj.group(2)
            new_name = re.sub(
                r"[\[\]]",
                "",
                f"{title} S{info.season}E{episode}{info.suffix}",
            )
            return new_name


def rename_advance(info: DownloadInfo):
    for rule in RULES:
        match_obj = re.match(rule, info.file_name, re.I)
        if match_obj is not None:
            episode = match_obj.group(2)
            new_name = re.sub(
                r"[\[\]]",
                "",
                f"{info.folder_name} S{info.season}E{episode}{info.suffix}",
            )
            return new_name


def rename_no_season_pn(info: DownloadInfo):
    for rule in RULES:
        match_obj = re.match(rule, info.file_name, re.I)
        if match_obj is not None:
            title = match_obj.group(1).strip()
            episode = match_obj.group(2)
            new_name = re.sub(
                r"[\[\]]",
                "",
                f"{title} E{episode}{info.suffix}",
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


if __name__ == '__main__':
    title = "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4"
    sub = parse_torrent(title, season=1)
    print(sub)
