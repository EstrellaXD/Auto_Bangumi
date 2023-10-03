import logging
import re
from os import PathLike

from module.conf import PLATFORM, settings
from module.models import Bangumi, BangumiUpdate

logger = logging.getLogger(__name__)

if PLATFORM == "Windows":
    from pathlib import PureWindowsPath as Path
else:
    from pathlib import Path


class TorrentPath:
    def __init__(self):
        pass

    @staticmethod
    def check_files(info):
        media_list = []
        subtitle_list = []
        for f in info.files:
            file_name = f.name
            suffix = Path(file_name).suffix
            if suffix.lower() in [".mp4", ".mkv"]:
                media_list.append(file_name)
            elif suffix.lower() in [".ass", ".srt"]:
                subtitle_list.append(file_name)
        return media_list, subtitle_list

    @staticmethod
    def _path_to_bangumi(save_path: PathLike[str] | str):
        # Split save path and download path
        save_parts = Path(save_path).parts
        download_parts = Path(settings.downloader.path).parts
        # Get bangumi name and season
        bangumi_name = ""
        season = 1
        for part in save_parts:
            if re.match(r"S\d+|[Ss]eason \d+", part):
                season = int(re.findall(r"\d+", part)[0])
            elif part not in download_parts:
                bangumi_name = part
        return bangumi_name, season

    @staticmethod
    def _file_depth(file_path: PathLike[str] | str):
        return len(Path(file_path).parts)

    def is_ep(self, file_path: PathLike[str] | str):
        return self._file_depth(file_path) <= 2

    @staticmethod
    def _gen_save_path(data: Bangumi | BangumiUpdate):
        folder = (
            f"{data.official_title} ({data.year})" if data.year else data.official_title
        )
        save_path = Path(settings.downloader.path) / folder / f"Season {data.season}"
        return str(save_path)

    @staticmethod
    def _rule_name(data: Bangumi):
        rule_name = (
            f"[{data.group_name}] {data.official_title} S{data.season}"
            if settings.bangumi_manage.group_tag
            else f"{data.official_title} S{data.season}"
        )
        return rule_name

    @staticmethod
    def _join_path(*args):
        return str(Path(*args))
