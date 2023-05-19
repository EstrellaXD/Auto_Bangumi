import re
import logging

from module.conf import settings
from module.models import BangumiData

if ":\\" in settings.downloader.path:
    import ntpath as path
else:
    import os.path as path

logger = logging.getLogger(__name__)


class TorrentPath:
    def __init__(self):
        self.download_path = settings.downloader.path

    @staticmethod
    def check_files(info):
        media_list = []
        subtitle_list = []
        for f in info.files:
            file_name = f.name
            suffix = path.splitext(file_name)[-1]
            if suffix.lower() in [".mp4", ".mkv"]:
                media_list.append(file_name)
            elif suffix.lower() in [".ass", ".srt"]:
                subtitle_list.append(file_name)
        return media_list, subtitle_list

    def _path_to_bangumi(self, save_path):
        # Split save path and download path
        save_parts = save_path.split(path.sep)
        download_parts = self.download_path.split(path.sep)
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
    def _file_depth(path):
        return len(path.split(path.sep))

    @staticmethod
    def is_ep(self, path):
        return self._file_depth(path) <= 2

    def _gen_save_path(self, data: BangumiData):
        folder = f"{data.official_title}({data.year})" if data.year else data.official_title
        save_path = path.join(self.download_path, folder, f"Season {data.season}")
        return save_path

    @staticmethod
    def _rule_name(data: BangumiData):
        rule_name = f"[{data.group_name}] {data.official_title} S{data.season}" \
            if settings.bangumi_manage.group_tag \
            else f"{data.official_title} S{data.season}"
        return rule_name

    @staticmethod
    def _join_path(*args):
        return path.join(*args)
