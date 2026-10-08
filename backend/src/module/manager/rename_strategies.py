"""重命名策略：由媒体文件信息生成目标文件名。

注意：这里的 title/bangumi_name 来自已存在于磁盘上的文件/文件夹名（单个路径
分量，不可能含分隔符），不做保留字符清洗——追加清洗会让既有做种库（如含 ":"
的标题）在升级后被整库批量重命名 (#721 评审)。

电影/剧场版：Title (Year).ext，不使用 SxxExx 编号。bangumi_name 由调用方传入，
与 gen_save_path 的文件夹命名保持一致 (Title (Year))。
"""

from collections.abc import Callable

from module.models import EpisodeFile, SubtitleFile

Strategy = Callable[[EpisodeFile | SubtitleFile, str, str, str], str]


def _subtitle(file_info: EpisodeFile | SubtitleFile) -> SubtitleFile:
    assert isinstance(
        file_info, SubtitleFile
    ), "subtitle methods require a SubtitleFile"
    return file_info


def pn(
    file_info: EpisodeFile | SubtitleFile, bangumi_name: str, season: str, episode: str
) -> str:
    if file_info.episode_type == "movie":
        return f"{file_info.title}{file_info.suffix}"
    return f"{file_info.title} S{season}E{episode}{file_info.suffix}"


def advance(
    file_info: EpisodeFile | SubtitleFile, bangumi_name: str, season: str, episode: str
) -> str:
    if file_info.episode_type == "movie":
        return f"{bangumi_name}{file_info.suffix}"
    return f"{bangumi_name} S{season}E{episode}{file_info.suffix}"


def subtitle_pn(
    file_info: EpisodeFile | SubtitleFile, bangumi_name: str, season: str, episode: str
) -> str:
    sub = _subtitle(file_info)
    if sub.episode_type == "movie":
        return f"{sub.title}.{sub.language}{sub.suffix}"
    return f"{sub.title} S{season}E{episode}.{sub.language}{sub.suffix}"


def subtitle_advance(
    file_info: EpisodeFile | SubtitleFile, bangumi_name: str, season: str, episode: str
) -> str:
    sub = _subtitle(file_info)
    if sub.episode_type == "movie":
        return f"{bangumi_name}.{sub.language}{sub.suffix}"
    return f"{bangumi_name} S{season}E{episode}.{sub.language}{sub.suffix}"


STRATEGIES: dict[str, Strategy] = {
    "pn": pn,
    "advance": advance,
    "subtitle_pn": subtitle_pn,
    "subtitle_advance": subtitle_advance,
}
