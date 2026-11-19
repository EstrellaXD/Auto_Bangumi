"""宿主管理凭据、代理与缓存的 TMDB 只读查询。绑定始终是可选项。"""

from dataclasses import dataclass
from typing import Literal, Protocol

MediaType = Literal["tv", "movie"]


@dataclass(frozen=True, slots=True)
class MediaReference:
    id: int
    media_type: MediaType
    title: str
    original_title: str
    year: str | None


@dataclass(frozen=True, slots=True)
class MediaDetails:
    reference: MediaReference
    seasons: tuple[tuple[int, int], ...]
    status: str


@dataclass(frozen=True, slots=True)
class EpisodeMetadata:
    season: int
    episode: int
    title: str
    air_date: str | None


class MetadataService(Protocol):
    async def search(
        self, query: str, *, media_type: MediaType = "tv", language: str = "zh-CN"
    ) -> tuple[MediaReference, ...]: ...

    async def get(
        self, media_id: int, *, media_type: MediaType = "tv", language: str = "zh-CN"
    ) -> MediaDetails: ...

    async def episodes(
        self, tv_id: int, season: int, *, language: str = "zh-CN"
    ) -> tuple[EpisodeMetadata, ...]: ...
