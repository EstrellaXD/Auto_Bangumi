"""重命名策略契约。

插件用 ``@provider(points.RENAME_STRATEGY, id="mystyle")`` 返回一个实现
:class:`RenameStrategy` 的对象；用户把「设置 → 番剧管理 → 重命名方式」
（``bangumi_manage.rename_method``）设为该 id 即可启用。

宿主对种子里的每个媒体文件和字幕文件各调用一次 ``target_name``。剧集偏移
已经应用到 :attr:`RenameInput.episode`，季度取自番剧文件夹（同样已含季度
偏移），策略只负责「拼名字」。
"""

from dataclasses import dataclass
from typing import Literal, Protocol

FileKind = Literal["media", "subtitle"]


@dataclass(frozen=True)
class RenameInput:
    """待重命名的一个文件。"""

    # 从文件名解析出的番剧标题
    title: str
    # 番剧文件夹名，如 ``"葬送的芙莉莲 (2023)"``
    bangumi_name: str
    season: int
    # 已应用剧集偏移；总集篇等半集保留小数（如 12.5）
    episode: int | float
    # 扩展名，含点，如 ``".mkv"`` / ``".ass"``
    suffix: str
    kind: FileKind = "media"
    # 字幕语言（如 ``"zh"`` / ``"zh-tw"``）；媒体文件为 None
    language: str | None = None
    # ``"episode"`` / ``"movie"`` / ``"special"``
    episode_type: str = "episode"
    # 文件在种子内的当前相对路径
    original_path: str = ""
    # 字幕组（可能为 None）。内置策略从不把它写进文件名
    group: str | None = None

    @property
    def full_suffix(self) -> str:
        """字幕为 ``.<语言><扩展名>``（如 ``.zh.ass``），媒体文件即 ``suffix``。"""
        if self.kind == "subtitle" and self.language:
            return f".{self.language}{self.suffix}"
        return self.suffix


class RenameStrategy(Protocol):
    def target_name(self, f: RenameInput) -> str:
        """返回文件在种子内的新相对路径（含扩展名）。

        返回 ``f.original_path`` 表示不改名。抛出异常、返回空字符串、绝对路径
        或含 ``..`` 的路径时，宿主记录错误并保持原路径。
        """
        ...
