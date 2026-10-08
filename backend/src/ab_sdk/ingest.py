"""ingest 流水线（RSS → 解析 → 匹配 → 过滤 → 元数据 → 添加种子）的插件契约。

钩子与 Provider 收到的都是只读快照（冻结 dataclass），不是数据库对象：
插件不能、也不应该直接修改宿主的 ORM 实例。需要修改时用
:func:`dataclasses.replace` 返回一个新副本。

扩展点一览（常量见 :mod:`ab_sdk.points`）：

- ``torrent.filter``（filter）：``accept(torrent, release, bangumi) -> Verdict``
- ``title.parsed``（transform）：``fix(release) -> release``
- ``torrent.adding``（transform）：``adjust(request: AddRequest) -> AddRequest``
- ``http.request``（transform）：``adjust(request: HttpRequest) -> HttpRequest``
- ``metadata_provider``（Provider）：返回 :class:`MetadataProvider`
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class TorrentInfo:
    """RSS 中的一条种子。"""

    name: str
    url: str
    homepage: str | None = None
    rss_id: int | None = None


@dataclass(frozen=True, slots=True)
class BangumiInfo:
    """番剧规则（订阅）的只读视图。"""

    id: int | None
    official_title: str
    title_raw: str
    season: int
    group_name: str | None = None
    episode_type: str = "episode"
    rss_link: str = ""
    save_path: str | None = None
    # 规则上的排除过滤（逗号分隔），宿主已在调用 torrent.filter 前应用过
    filter: str = ""


class Release(Protocol):
    """标题解析结果（``ParsedRelease``）的只读视图。

    宿主传入的是冻结 dataclass，``title.parsed`` 钩子用
    ``dataclasses.replace(release, group=...)`` 返回修改后的副本。
    下列字段之外的属性（``media_type``、``release_kind``、``codecs`` 等）
    同样可读，但在 SDK 1.0 之前不保证稳定。
    """

    @property
    def raw(self) -> str: ...

    @property
    def title_en(self) -> str | None: ...

    @property
    def title_zh(self) -> str | None: ...

    @property
    def title_jp(self) -> str | None: ...

    @property
    def group(self) -> str | None: ...

    @property
    def season(self) -> int | None: ...

    @property
    def episode(self) -> int | float | None: ...

    @property
    def resolution(self) -> str | None: ...

    @property
    def source(self) -> str | None: ...

    @property
    def subtitle(self) -> str | None: ...

    @property
    def year(self) -> int | None: ...


@dataclass(frozen=True, slots=True)
class AddRequest:
    """即将交给下载器的添加请求，``torrent.adding`` 钩子可返回修改后的副本。

    注意：

    - 整理/重命名只扫描 ``Bangumi`` 分类的种子；改掉 ``category`` 意味着
      AB 不再整理这些种子。
    - ``ab:<id>`` 标签用于重命名时查找番剧，钩子删掉它时宿主会补回。
    - 重命名会从 ``save_path`` 的 ``<番剧名>/Season N`` 结构推断番剧与季度，
      修改时请保留这一结构。
    """

    bangumi: BangumiInfo
    torrents: tuple[TorrentInfo, ...]
    save_path: str
    category: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """宿主发出的 GET 请求（RSS、种子文件、站点页面）。

    ``http.request`` 钩子可返回修改了 ``headers`` 的副本，例如为私有站点
    添加 Cookie 或替换 User-Agent::

        return replace(req, headers={**req.headers, "Cookie": "uid=1"})
    """

    method: str
    url: str
    headers: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Metadata:
    """番剧/电影的展示元数据。"""

    official_title: str
    season: int = 1
    year: str | None = None
    poster_link: str | None = None


@dataclass(frozen=True, slots=True)
class MetadataRequest:
    """新规则入库前的元数据补全请求。

    ``current`` 是解析器得出的当前值。Provider 返回完整的新
    :class:`Metadata`（通常是 ``replace(request.current, ...)``），
    返回 None 表示不修改。
    """

    kind: Literal["bangumi", "movie"]
    torrent: TorrentInfo
    language: str
    episode_type: str
    current: Metadata


class MetadataProvider(Protocol):
    """元数据源，按 RSS 订阅的「解析器」（``RSSItem.parser``）选择。"""

    async def enrich(self, request: MetadataRequest) -> Metadata | None: ...
