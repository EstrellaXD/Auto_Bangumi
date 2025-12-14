import logging
from pathlib import Path

from models import EpisodeFile, SubtitleFile
from module.utils import check_file

from module.parser.meta_parser import TitleMetaParser

logger = logging.getLogger(__name__)

SUBTITLE_LANG = {
    "zh-tw": ["tc", "cht", "繁", "zh-tw"],
    "zh": ["sc", "chs", "简", "zh"],
}


def get_subtitle_lang(subtitle_name: str) -> str:
    for key, value in SUBTITLE_LANG.items():
        for v in value:
            if v in subtitle_name.lower():
                return key
    return "zh"


def torrent_parser(
    torrent_name: str,
) -> EpisodeFile | SubtitleFile:
    """
    [LKSUB][Make Heroine ga Oosugiru!][01-12][720P]/[LKSUB][Make Heroine ga Oosugiru!][01][720P].mp4
    将 torrent 文件名解析为 EpisodeFile 或 SubtitleFile 对象
    """
    # 这是去掉路径中的目录部分,只保留文件名部分
    torrent_name = Path(torrent_name).name
    file_type = check_file(torrent_name)
    media_info = TitleMetaParser().parser(torrent_name)
    suffix = Path(torrent_name).suffix
    if file_type == "media":
        return EpisodeFile(
            **media_info.model_dump(),
            torrent_name=Path(torrent_name).stem,
            title=media_info.get_title(),
            suffix=suffix,
        )
    else:
        language = get_subtitle_lang(torrent_name)
        return SubtitleFile(
            **media_info.model_dump(),
            torrent_name=Path(torrent_name).stem,
            language=language,
            title=media_info.get_title(),
            suffix=suffix,
        )


if __name__ == "__main__":
    path = "LKSUB][Make Heroine ga Oosugiru!][01-12][720P]/[LKSUB][Make Heroine ga Oosugiru!][01][720P].mp4"
    print(torrent_parser(path))
