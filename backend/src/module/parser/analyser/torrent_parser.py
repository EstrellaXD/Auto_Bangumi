import logging
from pathlib import Path

from module.models import EpisodeFile, SubtitleFile
from module.parser.analyser.raw_parser import RawParser

logger = logging.getLogger(__name__)

SUBTITLE_LANG = {
    "zh-tw": ["tc", "cht", "繁", "zh-tw"],
    "zh": ["sc", "chs", "简", "zh"],
}


def get_path_basename(torrent_path: str) -> str:
    """
    返回路径的basename

    :param torrent_path: A string representing a path to a file.
    :type torrent_path: str
    :return: A string representing the basename of the given path.
    :rtype: str
    """
    return Path(torrent_path).name


def get_subtitle_lang(subtitle_name: str) -> str:
    for key, value in SUBTITLE_LANG.items():
        for v in value:
            if v in subtitle_name.lower():
                return key


def torrent_parser(
    torrent_name: str,
    file_type: str = "media",
) -> EpisodeFile | SubtitleFile:
    torrent_name = get_path_basename(torrent_name)
    media_info = RawParser().parser(torrent_name)
    suffix = Path(torrent_name).suffix
    title = media_info.title_en
    if media_info.title_zh:
        title = media_info.title_zh
    if media_info.title_jp:
        title = media_info.title_jp

    if file_type == "media":
        return EpisodeFile(
            media_path=torrent_name,
            group=media_info.group,
            title=title,
            season=media_info.season,
            episode=media_info.episode,
            suffix=suffix,
        )
    if file_type == "subtitle":
        language = get_subtitle_lang(torrent_name)
        return SubtitleFile(
            media_path=torrent_name,
            group=media_info.group,
            title=title,
            season=media_info.season,
            episode=media_info.episode,
            language=language,
            suffix=suffix,
        )


if __name__ == "__main__":
    path = "LKSUB][Make Heroine ga Oosugiru!][01-12][720P]/[LKSUB][Make Heroine ga Oosugiru!][01][720P].mp4'"
    print(get_path_basename(path))
