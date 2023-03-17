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


@dataclass
class SeasonInfo(dict):
    official_title: str
    title_raw: str
    season: int
    season_raw: str
    group: str
    filter: list | None
    offset: int | None
    dpi: str
    source: str
    subtitle: str
    added: bool
    eps_collect: bool



