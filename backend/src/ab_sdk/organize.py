"""整理（重命名）阶段由宿主发布的事件。

用 ``@subscribe(FileRenamed.kind)`` 订阅。事件在重命名真正发生之后发布，
订阅者在独立队列中异步执行，失败或超时不影响重命名流程。
"""

from dataclasses import dataclass
from typing import ClassVar

from .events import Event
from .rename import FileKind


@dataclass(frozen=True, slots=True)
class FileRenamed(Event):
    """下载器里的一个文件被重命名后发布（文件名已符合目标、无需改名时不发布）。

    路径都是下载器视角：``save_path`` 是种子的保存目录，``old_path`` /
    ``new_path`` 是种子内的相对路径。AB 与下载器不在同一台机器（或容器挂载
    路径不同）时，插件需要自行映射。
    """

    kind: ClassVar[str] = "file.renamed"
    torrent_hash: str
    # 匹配到的番剧 id；未能关联到番剧时为 None
    bangumi_id: int | None
    official_title: str
    season: int
    # 已应用剧集偏移
    episode: int | float
    old_path: str
    new_path: str
    save_path: str
    file_kind: FileKind


@dataclass(frozen=True, slots=True)
class TorrentOrganized(Event):
    """一个种子的媒体文件（以及随后的字幕）全部处理完成后发布。

    与种子的 ``ab:renamed`` 标签同时产生，每个种子通常只发布一次（打标签失败
    时下一轮会再处理并再次发布）。重命名方式为 ``none`` 时不发布。
    """

    kind: ClassVar[str] = "torrent.organized"
    torrent_hash: str
    torrent_name: str
    bangumi_id: int | None
    official_title: str
    save_path: str
    # 多文件合集种子（会被移动到 BangumiCollection 分类）
    collection: bool = False
