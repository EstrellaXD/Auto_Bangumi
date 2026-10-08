"""重命名路径生成（命名策略）。

``gen_path`` 把解析出的文件转成 :class:`ab_sdk.rename.RenameInput`（剧集偏移在
这里统一应用），再交给 ``rename_strategy`` 扩展点上 id 为重命名方式的策略。
内置 ``pn`` / ``advance`` / ``none`` 以 ``core`` 身份登记，插件可以提供更多。
"""

import logging
from pathlib import PurePath

from ab_sdk import points
from ab_sdk.rename import RenameInput, RenameStrategy
from module.models import EpisodeFile, SubtitleFile
from module.plugin import host

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


def format_season(season: int) -> str:
    return f"0{season}" if season < 10 else str(season)


# ---------------------------------------------------------------- core strategies
# 注意：group_tag 只影响 qB RSS 规则名（downloader/path.py 的 rule_name），
# 从不写进重命名后的文件名——已有做种媒体库的文件名必须保持稳定，
# 否则升级后会触发整库批量重命名，破坏 Plex/Jellyfin 索引与硬链接。
# title/bangumi_name 来自已存在于磁盘上的文件/文件夹名（单个路径分量，不可能
# 含分隔符），不做保留字符清洗——追加清洗会让既有做种库（如含 ":" 的标题）
# 在升级后被整库批量重命名 (#721 评审)。


class PnStrategy:
    """``{title} S01E05.mkv``：标题取自文件名解析结果。"""

    use_bangumi_name = False

    def target_name(self, f: RenameInput) -> str:
        base = f.bangumi_name if self.use_bangumi_name else f.title
        if f.episode_type == "movie":
            # 电影/剧场版：Title (Year).ext，不使用 SxxExx 编号。bangumi_name 与
            # gen_save_path 的文件夹命名保持一致 (Title (Year))
            return f"{base}{f.full_suffix}"
        season = format_season(f.season)
        episode = format_episode(f.episode)
        return f"{base} S{season}E{episode}{f.full_suffix}"


class AdvanceStrategy(PnStrategy):
    """``{番剧文件夹名} S01E05.mkv``。"""

    use_bangumi_name = True


class NoneStrategy:
    """不改名。"""

    def target_name(self, f: RenameInput) -> str:
        return f.original_path


CORE_STRATEGIES: dict[str, RenameStrategy] = {
    "pn": PnStrategy(),
    "advance": AdvanceStrategy(),
    "none": NoneStrategy(),
}


# ---------------------------------------------------------------- dispatch


def build_input(
    file_info: EpisodeFile | SubtitleFile, bangumi_name: str, episode_offset: int = 0
) -> RenameInput:
    language = file_info.language if isinstance(file_info, SubtitleFile) else None
    return RenameInput(
        title=file_info.title,
        bangumi_name=bangumi_name,
        # 季度取自文件夹名（"Season {season + season_offset}"），已含季度偏移
        season=file_info.season,
        episode=adjust_episode(file_info.episode, episode_offset),
        suffix=file_info.suffix,
        kind="media" if language is None else "subtitle",
        language=language,
        episode_type=file_info.episode_type,
        original_path=file_info.media_path,
        group=file_info.group,
    )


def _valid_target(path: object) -> bool:
    if not isinstance(path, str) or not path.strip():
        return False
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or PurePath(normalized).is_absolute():
        return False
    return ".." not in normalized.split("/")


def target_name(method: str, f: RenameInput) -> str:
    """用 ``method`` 对应的策略生成目标路径；策略缺失或出错时保持原路径。"""
    try:
        strategy = host.provider(points.RENAME_STRATEGY, method)
    except Exception:
        logger.exception("Failed to load rename method %s", method)
        return f.original_path
    if strategy is None:
        logger.error(f"Unknown rename method: {method}")
        return f.original_path
    try:
        result = strategy.target_name(f)
    except Exception as e:
        logger.error(
            "Rename method %s failed for %s, keeping path: %s",
            method,
            f.original_path,
            e,
        )
        return f.original_path
    if not _valid_target(result):
        logger.error(
            "Rename method %s produced an invalid path %r for %s, keeping path",
            method,
            result,
            f.original_path,
        )
        return f.original_path
    return result


def gen_path(
    file_info: EpisodeFile | SubtitleFile,
    bangumi_name: str,
    method: str,
    episode_offset: int = 0,
) -> str:
    """生成 ``file_info`` 在种子内的新路径。字幕（``SubtitleFile``）与媒体文件
    使用同一个重命名方式，差别体现在 :attr:`RenameInput.kind`。"""
    return target_name(method, build_input(file_info, bangumi_name, episode_offset))


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
