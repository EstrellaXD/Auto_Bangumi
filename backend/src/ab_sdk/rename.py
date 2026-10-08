"""organize 流水线（下载完成 → 分类 → 重命名 → 后处理）的插件契约。

扩展点一览（常量见 :mod:`ab_sdk.points`）：

- ``rename_strategy``（Provider）：返回 :class:`RenameStrategy`，id 即设置项
  ``bangumi_manage.rename_method`` 的取值
- ``media_files``（Provider）：返回 :class:`MediaFiles`，判断种子内文件的类别
- ``conflict_policy``（Provider）：返回 :class:`ConflictPolicy`，目标路径已被
  另一个种子占用时决定保留还是替换

``media_files`` 与 ``conflict_policy`` 目前只使用宿主自带的实现（id
:data:`CORE_ID`），插件实现的选择随 P2.5 的 ``plugins.slots`` 一起提供。

整理完成后宿主发布 :class:`ab_sdk.events.FileRenamed` 与
:class:`ab_sdk.events.TorrentOrganized`，插件用 ``@subscribe`` 接收。
"""

from dataclasses import dataclass
from typing import Literal, Protocol

FileKind = Literal["media", "subtitle"]
MediaKind = Literal["media", "subtitle", "ignore"]
ConflictAction = Literal["hold", "replace"]

# media_files / conflict_policy 的宿主实现 id
CORE_ID = "default"


def pad(value: int | float, width: int = 2) -> str:
    """把季号 / 集数的整数部分补零到 ``width`` 位，小数部分原样保留。

    ``pad(5) == "05"``、``pad(12) == "12"``、``pad(9.5) == "09.5"``、
    ``pad(12.0) == "12"``。总集篇等半集（12.5）必须保留小数，否则会覆盖同季的
    整数集 (#667)。内置 pn / advance 与模板的 ``pad`` 过滤器都用它。
    """
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    whole, dot, fraction = str(value).partition(".")
    return whole.zfill(width) + dot + fraction


@dataclass(frozen=True, slots=True)
class RenameInput:
    """一个待重命名文件。

    ``episode`` 已应用番剧的集数偏移；``season`` 来自保存目录（已含季度偏移）。
    ``title`` 解析自文件名，``bangumi_name`` 是保存目录的番剧文件夹名（电影为
    ``Title (Year)``）。两者都是单个路径分量，宿主不做保留字符清洗。
    """

    kind: FileKind
    media_path: str  # 种子内的原相对路径
    title: str
    bangumi_name: str
    season: int
    episode: int | float
    suffix: str  # 含点，如 ".mkv"
    episode_type: str = "episode"  # episode | movie | special
    language: str = ""  # 字幕语言（kind == "subtitle"），如 "zh"、"zh-tw"
    group: str | None = None


class RenameSkipped(Exception):
    """策略无法为该文件给出名字时抛出：宿主保留原文件名，并为该种子发一条通知。

    与其它异常不同，它表示「输入或用户配置有问题」，不计入插件熔断。
    """


class RenameStrategy(Protocol):
    def target_name(self, f: RenameInput) -> str:
        """返回种子内的新相对路径（通常只是文件名，即把文件移到种子根目录）。

        返回原路径 ``f.media_path`` 表示不改名。须为非空字符串，否则按插件
        失败处理（计入熔断）并保留原文件名。
        """
        ...


class MediaFiles(Protocol):
    def classify(self, path: str) -> MediaKind:
        """种子内文件的类别：``media`` 重命名为正片，``subtitle`` 随正片重命名，
        ``ignore`` 不处理。"""
        ...


@dataclass(frozen=True, slots=True)
class Revision:
    """严格解析出的发布身份；只有同一身份、版本号更高时才算版本升级。"""

    bangumi_id: int
    media_type: str
    season: int
    episode: int | float
    group: str
    resolution: str
    revision: int


@dataclass(frozen=True, slots=True)
class RevisionTask:
    """下载器中的一个种子任务。"""

    hash: str
    name: str
    file_count: int
    revision: Revision | None  # 标题解析不完整时为 None


@dataclass(frozen=True, slots=True)
class ConflictRequest:
    """新种子（``incoming``）的规范目标路径已被其它任务（``owners``）占用。"""

    target_path: str
    incoming: RevisionTask
    owners: tuple[RevisionTask, ...]
    # 用户在设置中选择的版本冲突策略（bangumi_manage.revision_conflict_policy）
    configured: ConflictAction
    # 唯一占用者与新种子是同一发布、且新种子版本号更高
    strict_upgrade: bool


@dataclass(frozen=True, slots=True)
class ConflictDecision:
    action: ConflictAction
    reason: str = ""  # hold 时展示给用户的原因


class ConflictPolicy(Protocol):
    def decide(self, request: ConflictRequest) -> ConflictDecision:
        """``replace`` 会删除旧任务及其文件。宿主只在「唯一占用者、双方都是
        单文件种子、双方身份完整」时执行替换，否则一律按 ``hold`` 处理。"""
        ...
