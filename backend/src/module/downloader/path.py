import logging
import re
from functools import lru_cache
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
    def check_files(files_name: list[str]):
        media_list = []
        subtitle_list = []
        for file_name in files_name:
            suffix = Path(file_name).suffix
            if suffix.lower() in [".mp4", ".mkv"]:
                media_list.append(file_name)
            elif suffix.lower() in [".ass", ".srt"]:
                subtitle_list.append(file_name)
        return media_list, subtitle_list

    @staticmethod
    @lru_cache(maxsize=20)
    def path_to_bangumi(save_path: PathLike[str] | str):

        # Split save path and download path
        save_path = Path(save_path)
        download_path = Path(settings.downloader.path)
        try:
            bangumi_path = save_path.relative_to(download_path)
            bangumi_parts = bangumi_path.parts
        except ValueError as e:
            logging.warning(f"[Path] {e}")
            bangumi_parts = save_path.parts
        # Get bangumi name and season
        bangumi_name = ""
        season = 1
        for part in bangumi_parts:
            if re.match(r"S\d+|[Ss]eason \d+", part):
                season = int(re.findall(r"\d+", part)[0])
            else:
                bangumi_name = part
        return bangumi_name, season

    @staticmethod
    def _file_depth(file_path: PathLike[str] | str):
        return len(Path(file_path).parts)

    def is_ep(self, file_path: PathLike[str] | str):
        return self._file_depth(file_path) <= 2

    @staticmethod
    def gen_save_path(data: Bangumi | BangumiUpdate):
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
