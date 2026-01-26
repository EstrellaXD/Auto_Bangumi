import logging
import re
from collections import OrderedDict
from pathlib import Path

from module.models import EpisodeFile, SubtitleFile

logger = logging.getLogger(__name__)

# LRU cache for torrent_parser results to avoid repeated regex parsing
_PARSER_CACHE_MAX_SIZE = 512
_parser_cache: OrderedDict[tuple, EpisodeFile | SubtitleFile | None] = OrderedDict()

PLATFORM = "Unix"

RULES = [
    r"(.*) - (\d{1,4}(?:\.\d{1,2})?(?!\d|p))(?:v\d{1,2})?(?: )?(?:END)?(.*)",
    r"(.*)[\[\ E](\d{1,4}(?:\.\d{1,2})?)(?:v\d{1,2})?(?: )?(?:END)?[\]\ ](.*)",
    r"(.*)\[(?:第)?(\d{1,4}(?:\.\d{1,2})?)[话集話](?:END)?\](.*)",
    r"(.*)第?(\d{1,4}(?:\.\d{1,2})?)[话話集](?:END)?(.*)",
    r"(.*)(?:S\d{2})?EP?(\d{1,4}(?:\.\d{1,2})?)(.*)",
]

COMPILED_RULES = [re.compile(rule, re.I) for rule in RULES]

SUBTITLE_LANG = {
    "zh-tw": ["tc", "cht", "繁", "zh-tw"],
    "zh": ["sc", "chs", "简", "zh"],
}


def get_path_basename(torrent_path: str) -> str:
    """
    Returns the basename of a path string.

    :param torrent_path: A string representing a path to a file.
    :type torrent_path: str
    :return: A string representing the basename of the given path.
    :rtype: str
    """
    return Path(torrent_path).name


_GROUP_SPLIT_RE = re.compile(r"[\[\]()【】（）]")


def get_group(group_and_title) -> tuple[str | None, str]:
    n = [x for x in _GROUP_SPLIT_RE.split(group_and_title) if x]
    if len(n) > 1:
        if re.match(r"\d+", n[1]):
            return None, group_and_title
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
            if v in subtitle_name.lower():
                return key


def torrent_parser(
    torrent_path: str,
    torrent_name: str | None = None,
    season: int | None = None,
    file_type: str = "media",
) -> EpisodeFile | SubtitleFile | None:
    # Check cache first to avoid repeated regex parsing
    cache_key = (torrent_path, torrent_name, season, file_type)
    if cache_key in _parser_cache:
        # Move to end to mark as recently used
        _parser_cache.move_to_end(cache_key)
        return _parser_cache[cache_key]

    result = _torrent_parser_impl(torrent_path, torrent_name, season, file_type)

    # Store in cache with LRU eviction
    _parser_cache[cache_key] = result
    if len(_parser_cache) > _PARSER_CACHE_MAX_SIZE:
        _parser_cache.popitem(last=False)  # Remove oldest item

    return result


def _torrent_parser_impl(
    torrent_path: str,
    torrent_name: str | None = None,
    season: int | None = None,
    file_type: str = "media",
) -> EpisodeFile | SubtitleFile | None:
    """Internal implementation of torrent_parser without caching."""
    media_path = get_path_basename(torrent_path)
    match_names = [torrent_name, media_path]
    if torrent_name is None:
        match_names = match_names[1:]
    for match_name in match_names:
        for compiled_rule in COMPILED_RULES:
            match_obj = compiled_rule.match(match_name)
            if match_obj:
                group, title = get_group(match_obj.group(1))
                if not season:
                    title, season = get_season_and_title(title)
                else:
                    title, _ = get_season_and_title(title)
                episode = match_obj.group(2)
                suffix = Path(torrent_path).suffix
                if file_type == "media":
                    return EpisodeFile(
                        media_path=torrent_path,
                        group=group,
                        title=title,
                        season=season,
                        episode=episode,
                        suffix=suffix,
                    )
                elif file_type == "subtitle":
                    language = get_subtitle_lang(media_path)
                    return SubtitleFile(
                        media_path=torrent_path,
                        group=group,
                        title=title,
                        season=season,
                        language=language,
                        episode=episode,
                        suffix=suffix,
                    )
    return None


if __name__ == "__main__":
    ep = torrent_parser(
        "/不时用俄语小声说真心话的邻桌艾莉同学/Season 1/不时用俄语小声说真心话的邻桌艾莉同学 S01E02.mp4"
    )
    print(ep)

    ep = torrent_parser(
        "/downloads/Bangumi/关于我转生变成史莱姆这档事 (2018)/Season 3/[ANi] 關於我轉生變成史萊姆這檔事 第三季 - 48.5 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
    )
    print(ep)

    ep = torrent_parser(
        "/downloads/Bangumi/关于我转生变成史莱姆这档事 (2018)/Season 3/[ANi] 關於我轉生變成史萊姆這檔事 第三季 - 48.5 [1080P][Baha][WEB-DL][AAC AVC][CHT].srt",
        file_type="subtitle",
    )
    print(ep)
