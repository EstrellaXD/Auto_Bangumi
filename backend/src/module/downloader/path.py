import logging
import re
from functools import lru_cache
from os import PathLike

from module.conf import settings
from module.models import Bangumi, BangumiUpdate

if r"//" in settings.downloader.path:
    from pathlib import PureWindowsPath as Path
else:
    from pathlib import Path
logger = logging.getLogger(__name__)


class TorrentPath:

    def __init__(self):
        self.download_path = Path(settings.downloader.path)

    def check_file(self, file_path: PathLike[str] | str):
        suffix = Path(file_path).suffix
        if suffix.lower() in [".mp4", ".mkv"]:
            return "media"
        elif suffix.lower() in [".ass", ".srt"]:
            return "subtitle"

    def check_files(self, files_name: list[str]):
        media_list = []
        subtitle_list = []
        for file_name in files_name:
            file_type = self.check_file(file_name)
            if file_type == "media":
                media_list.append(file_name)
            elif file_type == "subtitle":
                subtitle_list.append(file_name)
        return media_list, subtitle_list

    @lru_cache(maxsize=20)
    def path_to_bangumi(
        self, save_path: PathLike[str] | str, download_path: PathLike[str] | str = ""
    ) -> tuple[str, int]:

        # Split save path and download path
        save_path = Path(save_path)
        if not download_path:
            download_path = self.download_path
        else:
            download_path = Path(download_path)
        bangumi_name = ""
        season = 0
        try:
            # 理论上 save_path 是 download_path 的子路径
            # 会 返回 形如 "物语系列/Season 5"
            bangumi_path = save_path.relative_to(download_path)
            bangumi_parts = bangumi_path.parts
        except ValueError as e:
            logger.warning(f"[Path] {e} is not a subpath of {download_path}")
            return bangumi_name, season
        # Get bangumi name and season
        # bangumi_parts 只会是[bangumi_name,Season]
        bangumi_name = bangumi_parts[0]
        if re.match(r"S\d+|[Ss]eason \d+", bangumi_parts[-1]):
            season = int(re.findall(r"\d+", bangumi_parts[-1])[0])
        return bangumi_name, season

    def _file_depth(self, file_path: PathLike[str] | str):
        return len(Path(file_path).parts)

    def is_ep(self, file_path: PathLike[str] | str):
        return self._file_depth(file_path) <= 2

    def gen_save_path(self, data: Bangumi | BangumiUpdate):
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

    def _join_path(self, *args):
        return str(Path(*args))


if __name__ == "__main__":

    path = "/Downloads/Bangumi/Kono Subarashii Sekai ni Shukufuku wo!/Season 2/"
    print(TorrentPath().path_to_bangumi(path, "/Downloads/Bangumi"))
