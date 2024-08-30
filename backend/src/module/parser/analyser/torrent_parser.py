import logging

from module.conf import PLATFORM
from module.models import EpisodeFile, SubtitleFile
from module.parser.analyser.raw_parser import RawParser

if PLATFORM == "Windows":
    from pathlib import PureWindowsPath as Path
else:
    from pathlib import Path
logger = logging.getLogger(__name__)

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


def get_subtitle_lang(subtitle_name: str) -> str:
    for key, value in SUBTITLE_LANG.items():
        for v in value:
            if v in subtitle_name.lower():
                return key


def torrent_parser(
    torrent_path: str,
    torrent_name: str,
    file_type: str = "media",
    season = 0,
) -> EpisodeFile | SubtitleFile:

    torrent_name = get_path_basename(torrent_name)
    if not season and torrent_path:
        season = RawParser(torrent_path).parser().season
    media_info = RawParser(torrent_name).parser()
    suffix = Path(torrent_name).suffix
    title = media_info.title_en
    if media_info.title_zh:
        title = media_info.title_zh
    if media_info.title_jp:
        title = media_info.title_jp

    if not season:
        season = media_info.season

    print(media_info)
    if file_type == "media":
        return EpisodeFile(
            media_path= torrent_name,
            group=media_info.group,
            title=title,
            season=season,
            episode=media_info.episode,
            suffix=suffix,
        )
    if file_type == "subtitle":
        language = get_subtitle_lang(torrent_name)
        return SubtitleFile(
            media_path=torrent_name,
            group=media_info.group,
            title=title,
            season=season,
            episode=media_info.episode,
            language=language,
            suffix=suffix,
        )


if __name__ == "__main__":
    path = "test/season 1"
    base = torrent_parser(torrent_path=path,torrent_name="物语系列 S05E06.5.mp4")
    file_info = EpisodeFile(title="test",season=1,episode=6.5,suffix=".mp4",media_path=".")
    print(file_info)
    if file_info.episode.is_integer():
        print(file_info.episode)
        episode = f"{int(file_info.episode):02d}"
        print(episode)
    else:
        episode = f"{file_info.episode:04.1f}"
        print(episode)

    # lang = get_subtitle_lang(base)
