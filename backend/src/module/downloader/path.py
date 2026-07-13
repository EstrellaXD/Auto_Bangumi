import logging
import re
from os import PathLike
from pathlib import PureWindowsPath

from module.conf import PLATFORM, settings
from module.models import Bangumi, BangumiUpdate
from module.models.movie import Movie, MovieUpdate

logger = logging.getLogger(__name__)

if PLATFORM == "Windows":
    # PLATFORM is a runtime config value, not the actual OS (`sys.platform`),
    # so mypy can't special-case this branch: it type-checks both arms and
    # sees two incompatible bindings for the same name `Path`. Both classes
    # share the PurePath interface (.suffix/.parts/joining) used below.
    from pathlib import PureWindowsPath as Path  # type: ignore[assignment]
else:
    from pathlib import Path  # type: ignore[assignment]


_MEDIA_SUFFIXES = frozenset({".mp4", ".mkv"})
_SUBTITLE_SUFFIXES = frozenset({".ass", ".srt"})

# Windows/qB 保留字符 + 控制字符：出现在路径片段里会被下载器拆成多级
# 目录或直接丢字（qB 静默截断），必须在拼路径前替换掉 (#721)
_ILLEGAL_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_path_fragment(name: str) -> str:
    """把单个路径片段（文件夹名或文件名，不含分隔符）里的保留字符替换为空格。

    多余空白折叠为单个空格；Windows 不允许目录/文件名以点或空格结尾，
    一并去掉。幂等：对已合法的名字原样返回。
    """
    cleaned = _ILLEGAL_PATH_CHARS_RE.sub(" ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.rstrip(". ")


def check_files(files: list[dict]):
    media_list = []
    subtitle_list = []
    for f in files:
        file_name = f["name"]
        suffix = Path(file_name).suffix.lower()
        if suffix in _MEDIA_SUFFIXES:
            media_list.append(file_name)
        elif suffix in _SUBTITLE_SUFFIXES:
            subtitle_list.append(file_name)
    return media_list, subtitle_list


def path_to_bangumi(save_path: PathLike[str] | str, torrent_name: str = ""):
    # Use PureWindowsPath regardless of the host AB runs on: it accepts
    # both "\" and "/" separators, so a qBittorrent-on-Windows save_path
    # reaching a Linux AB still splits into segments correctly (#1016).
    save_parts = PureWindowsPath(save_path).parts
    download_parts = PureWindowsPath(settings.downloader.path).parts
    # Get bangumi name and season
    bangumi_name = ""
    season = 1
    for part in save_parts:
        if re.match(r"S\d+|[Ss]eason \d+", part):
            season = int(re.findall(r"\d+", part)[0])
        elif part not in download_parts:
            bangumi_name = part
    if not bangumi_name:
        bangumi_name = torrent_name
    return bangumi_name, season


def file_depth(file_path: PathLike[str] | str):
    return len(Path(file_path).parts)


def is_ep(file_path: PathLike[str] | str):
    return file_depth(file_path) <= 2


def _media_folder(data: Bangumi | BangumiUpdate | Movie | MovieUpdate) -> str:
    title = data.official_title or "Unknown Bangumi"
    folder = sanitize_path_fragment(f"{title} ({data.year})" if data.year else title)
    if folder:
        return folder
    # 标题全由保留字符组成时清洗结果为空——不能让所有这类条目
    # 坍缩到同一个下载目录里
    return "Unknown Bangumi"


def gen_save_path(data: Bangumi | BangumiUpdate | Movie | MovieUpdate) -> str:
    """Generate save path for a bangumi.

    The save path uses the adjusted season number (season + season_offset)
    so files are saved directly to the correct season folder.

    Movies use a flat "Title (Year)" layout with no season subfolder, and
    specials/OVA/OAD land in "Season 0" (Jellyfin/Plex convention) instead of
    being interleaved with regular episodes.
    """
    folder = _media_folder(data)
    episode_type = getattr(data, "episode_type", "episode")
    if isinstance(data, (Movie, MovieUpdate)) or episode_type == "movie":
        # 电影/剧场版：Title (Year)/Title (Year).ext，不建 Season 子目录
        return str(Path(settings.downloader.path) / folder)
    # Apply season_offset to get the adjusted season number for the folder
    adjusted_season = data.season + getattr(data, "season_offset", 0)
    # 季号下限：普通剧集最小为 1——偏移到 Season 0 会被 Plex/Jellyfin 当作
    # 特别篇；只有特别篇（special）允许合法落入第 0 季
    min_season = 0 if episode_type == "special" else 1
    if adjusted_season < min_season:
        adjusted_season = data.season
        logger.warning(
            f"Season offset would result in invalid season for {data.official_title}, using original season"
        )
    save_path = Path(settings.downloader.path) / folder / f"Season {adjusted_season}"
    return str(save_path)


def gen_movie_save_path(data: Movie | MovieUpdate) -> str:
    """Generate the flat save directory used by a movie/gekijouban."""
    return str(Path(settings.downloader.path) / _media_folder(data))


def movie_rule_name(data: Movie) -> str:
    return (
        f"[{data.group_name}] {data.official_title}"
        if settings.bangumi_manage.group_tag
        else data.official_title
    )


def rule_name(data: Bangumi):
    name = (
        f"[{data.group_name}] {data.official_title} S{data.season}"
        if settings.bangumi_manage.group_tag
        else f"{data.official_title} S{data.season}"
    )
    return name


def join_path(*args):
    return str(Path(*args))
