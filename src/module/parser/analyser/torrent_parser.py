import re
import logging
import os.path as unix_path
import ntpath as win_path

from module.models import EpisodeFile, SubtitleFile

logger = logging.getLogger(__name__)

PLATFORM = "Unix"

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


def torrent_parser(torrent_path: str, season: int | None = None, file_type: str = "media") -> EpisodeFile | SubtitleFile:
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
