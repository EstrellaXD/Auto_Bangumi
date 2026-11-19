"""完整整理器与已发布媒体库文件。文件规则、执行意图及所有权由插件保存。"""

from dataclasses import dataclass
from typing import Literal, Protocol

from .bangumi import BangumiSnapshot
from .downloads import DownloadTask, FileSnapshot


@dataclass(frozen=True, slots=True)
class LibraryFile:
    file_id: str
    path: str
    kind: Literal["media", "subtitle", "music", "archive"]


@dataclass(frozen=True, slots=True)
class OrganizeRequest:
    task: DownloadTask
    files: FileSnapshot
    bangumi: BangumiSnapshot


@dataclass(frozen=True, slots=True)
class OrganizeResult:
    operation_id: str
    files: tuple[LibraryFile, ...]
    # 插件可选提供 TMDB 等身份；不是整理准入条件，也不包含下载器状态。
    media_identity: str = ""


class Organizer(Protocol):
    async def organize(self, request: OrganizeRequest) -> OrganizeResult | None:
        """文件可分别完成；只提交本次成功发布的文件，重试返回同一操作 id。"""
        ...


class LibraryService(Protocol):
    async def selected(self) -> str: ...

    async def commits(
        self,
        *,
        bangumi_id: int | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> tuple[tuple[dict, ...], str | None]:
        """启动补查；事件只用于唤醒，不能代替持久记录。"""
        ...
