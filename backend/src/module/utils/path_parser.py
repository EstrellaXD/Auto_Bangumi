"""
对 windowns 上解析 linux 路径的工具函数
和 linux 上解析 windows 路径的工具函数
"""

import logging
import re
from os import PathLike
from pathlib import Path

from module.models import Bangumi, BangumiUpdate

# TODO: 暂时放弃 Windows 路径解析,也就是 ab 和 qb 不在一个系统上, 这时候整个复杂度太高了,后面再说了
logger = logging.getLogger(__name__)


def get_path_basename(torrent_path: str) -> str:
    """
    返回路径的basename

    :param torrent_path: A string representing a path to a file.
    :type torrent_path: str
    :return: A string representing the basename of the given path.
    :rtype: str
    """
    return Path(torrent_path).name


def check_file(file_path: str):
    file_path = get_path_basename(file_path)
    suffix = Path(file_path).suffix
    if suffix.lower() in [".mp4", ".mkv"]:
        return "media"
    elif suffix.lower() in [".ass", ".srt"]:
        return "subtitle"


def check_files(files_name: list[str]):
    media_list = []
    subtitle_list = []
    for file_name in files_name:
        file_type = check_file(file_name)
        if file_type == "media":
            media_list.append(file_name)
        elif file_type == "subtitle":
            subtitle_list.append(file_name)
    return media_list, subtitle_list


def path_to_bangumi(
    save_path: PathLike[str] | str, download_path: PathLike[str] | str
) -> tuple[str, int]:
    # Split save path and download path
    save_path = Path(save_path)
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


def gen_save_path(save_path: str, data: Bangumi | BangumiUpdate) -> str:
    # TODO: official_title 可能会有特殊字符,需要处理
    folder = data.official_title
    if data.year:
        folder += f" ({data.year})"
    folder = Path(folder)
    season = Path(f"Season {data.season}")
    return str(Path(save_path) / folder / season)


if __name__ == "__main__":
    path = "/Downloads/Bangumi/Kono Subarashii Sekai ni Shukufuku wo!/Season 2/"
    # bangumi_name = "[整理搬运] 乱马 1/2 (らんま½) (Ranma ½)：TV动画 (1989年首播版)+剧场版+OVA+CD+漫画+其他；日语音轨; 外挂简中字幕 (整理时间：2023.11.mp4"
    # bangumi_name = bangumi_name.replace("/", ":")
    # print(bangumi_name)
    # a = Path(bangumi_name)
    print(a.name)

    # print(path_to_bangumi(path, "/Downloads/Bangumi"))
