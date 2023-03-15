from dataclasses import dataclass


@dataclass
class MatchRule:
    keyword: str
    filter: list
    rss_link: str


@dataclass
class GroupFilter:
    name: str
    filter: list


@dataclass
class Episode:
    title_en: str | None
    title_zh: str | None
    title_jp: str | None
    season: int
    season_raw: str
    episode: int
    sub: str
    group: str
    resolution: str
    source: str
