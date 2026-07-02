import logging
import re
from os import PathLike
from pathlib import PureWindowsPath

from module.conf import PLATFORM, settings
from module.models import Bangumi, BangumiUpdate

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


def gen_save_path(data: Bangumi | BangumiUpdate):
    """Generate save path for a bangumi.

    The save path uses the adjusted season number (season + season_offset)
    so files are saved directly to the correct season folder.

    Movies use a flat "Title (Year)" layout with no season subfolder, and
    specials/OVA/OAD land in "Season 0" (Jellyfin/Plex convention) instead of
    being interleaved with regular episodes.
    """
    folder = (
        f"{data.official_title} ({data.year})" if data.year else data.official_title
    )
    episode_type = getattr(data, "episode_type", "episode")
    if episode_type == "movie":
        # 电影/剧场版：Title (Year)/Title (Year).ext，不建 Season 子目录
        return str(Path(settings.downloader.path) / folder)
    # Apply season_offset to get the adjusted season number for the folder
    adjusted_season = data.season + getattr(data, "season_offset", 0)
    if adjusted_season < 0:
        adjusted_season = data.season  # Safety: don't go below 0 (0 = specials)
        logger.warning(
            f"[Path] Season offset would result in invalid season for {data.official_title}, using original season"
        )
    save_path = Path(settings.downloader.path) / folder / f"Season {adjusted_season}"
    return str(save_path)


def rule_name(data: Bangumi):
    name = (
        f"[{data.group_name}] {data.official_title} S{data.season}"
        if settings.bangumi_manage.group_tag
        else f"{data.official_title} S{data.season}"
    )
    return name


def join_path(*args):
    return str(Path(*args))
