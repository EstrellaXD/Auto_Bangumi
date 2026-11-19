"""已有番剧的只读有效配置。revision 是配置内容摘要，不是集号。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BangumiSnapshot:
    id: int
    official_title: str
    title_raw: str
    year: str | None
    episode_type: str
    season: int
    season_offset: int
    episode_offset: int
    effective_season: int
    group_name: str | None
    filter: str
    rss_link: str
    save_path: str | None
    downloader_id: str | None
    deleted: bool
    archived: bool
    revision: str
    dpi: str | None = None
    source: str | None = None
    subtitle: str | None = None
    preferred_group: str | None = None
    preferred_resolution: str | None = None
    title_aliases: str | None = None


class BangumiService(Protocol):
    async def get(self, bangumi_id: int) -> BangumiSnapshot | None: ...
