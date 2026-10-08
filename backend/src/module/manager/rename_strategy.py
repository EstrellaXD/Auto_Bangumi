"""重命名路径生成（命名策略）。

``gen_path`` 根据重命名方式生成种子内的新文件路径；剧集偏移在这里统一应用。
"""

import logging
from pathlib import PurePath

from module.models import EpisodeFile, SubtitleFile

logger = logging.getLogger(__name__)


def adjust_episode(original: int | float, episode_offset: int) -> int | float:
    if original == 0 and episode_offset != 0:
        # Episode 0 is a special/OVA — never apply offset to avoid
        # overwriting regular episodes (see issue #977)
        return 0
    adjusted = original + episode_offset
    # An offset producing a non-positive result (e.g., EP5 + offset -10)
    # is almost always a misconfiguration, so revert to original.
    if adjusted < 0 or (adjusted == 0 and original > 0):
        logger.warning(
            f"Episode offset {episode_offset} would make episode {original} non-positive, ignoring offset"
        )
        return original
    return adjusted


def format_episode(episode: int | float) -> str:
    # 总集篇等半集（12.5）保留小数，否则会覆盖同季的整数集 (#667)；
    # 整数值沿用两位补零
    if isinstance(episode, float) and episode.is_integer():
        episode = int(episode)
    return f"0{episode}" if episode < 10 else str(episode)


def gen_path(
    file_info: EpisodeFile | SubtitleFile,
    bangumi_name: str,
    method: str,
    episode_offset: int = 0,
    season_offset: int = 0,  # Kept for API compatibility, but no longer used
) -> str:
    # Season comes from the folder name which already includes the offset
    # (folder is now "Season {season + season_offset}")
    # So we use file_info.season directly without applying offset again
    season_num = file_info.season
    season = f"0{season_num}" if season_num < 10 else season_num
    episode = format_episode(adjust_episode(file_info.episode, episode_offset))
    # 注意：group_tag 只影响 qB RSS 规则名（downloader/path.py 的 rule_name），
    # 从不写进重命名后的文件名——已有做种媒体库的文件名必须保持稳定，
    # 否则升级后会触发整库批量重命名，破坏 Plex/Jellyfin 索引与硬链接
    if method == "none" or method == "subtitle_none":
        return file_info.media_path
    # 注意：这里的 title/bangumi_name 来自已存在于磁盘上的文件/文件夹名
    # （单个路径分量，不可能含分隔符），不做保留字符清洗——追加清洗会让
    # 既有做种库（如含 ":" 的标题）在升级后被整库批量重命名 (#721 评审)
    title = file_info.title
    if file_info.episode_type == "movie":
        # 电影/剧场版：Title (Year).ext，不使用 SxxExx 编号。bangumi_name 由
        # 调用方传入，与 gen_save_path 的文件夹命名保持一致 (Title (Year))
        base = bangumi_name if "advance" in method else title
        if method.startswith("subtitle_"):
            assert isinstance(
                file_info, SubtitleFile
            ), "subtitle methods require a SubtitleFile"
            return f"{base}.{file_info.language}{file_info.suffix}"
        return f"{base}{file_info.suffix}"
    elif method == "pn":
        return f"{title} S{season}E{episode}{file_info.suffix}"
    elif method == "advance":
        return f"{bangumi_name} S{season}E{episode}{file_info.suffix}"
    elif method == "subtitle_pn":
        assert isinstance(
            file_info, SubtitleFile
        ), "subtitle_pn requires a SubtitleFile"
        return f"{title} S{season}E{episode}.{file_info.language}{file_info.suffix}"
    elif method == "subtitle_advance":
        assert isinstance(
            file_info, SubtitleFile
        ), "subtitle_advance requires a SubtitleFile"
        return (
            f"{bangumi_name} S{season}E{episode}.{file_info.language}{file_info.suffix}"
        )
    else:
        logger.error(f"Unknown rename method: {method}")
        return file_info.media_path


def gen_movie_extra_path(new_path: str, media_path: str) -> str:
    """多文件电影种子中，非主文件在干净名（Title (Year).ext）基础上追加
    原始文件名词干作区分，避免与主文件生成相同目标名互相冲突/覆盖；
    词干若已带 "Title (Year) - " 前缀则先剥离，保证重命名幂等。"""
    suffix = PurePath(new_path).suffix
    base = new_path[: -len(suffix)] if suffix else new_path
    stem = PurePath(media_path).stem
    prefix = f"{base} - "
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    return f"{base} - {stem}{suffix}"
