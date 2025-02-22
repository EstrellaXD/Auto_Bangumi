from dataclasses import dataclass
from typing import TypedDict

# 一些没有用到的类型,但又感觉以后可能会用到,所以先写在这里


class Genre(TypedDict):
    id: int
    name: str


@dataclass
class Network(TypedDict):
    id: int
    logo_path: str | None
    name: str
    origin_country: str


@dataclass
class LastEpisodeToAir(TypedDict):
    id: int
    name: str
    overview: str
    vote_average: float
    vote_count: int
    air_date: str
    episode_number: int
    episode_type: str
    production_code: str
    runtime: int
    season_number: int
    show_id: int
    still_path: str


@dataclass
class ProductionCompany(TypedDict):
    id: int
    name: str
    origin_country: str
    logo_path: str | None = None


@dataclass
class Season(TypedDict):
    air_date: str | None
    episode_count: int
    id: int
    name: str
    overview: str
    season_number: int
    vote_average: float
    poster_path: str | None = None


class TVShow(TypedDict):
    adult: bool
    backdrop_path: str
    created_by: list[dict]
    episode_run_time: list[int]
    first_air_date: str
    genres: list[Genre]
    homepage: str
    id: int
    in_production: bool
    languages: list[str]
    last_air_date: str
    last_episode_to_air: LastEpisodeToAir
    name: str
    networks: list[Network]
    number_of_episodes: int
    number_of_seasons: int
    origin_country: list[str]
    original_language: str
    original_name: str
    overview: str
    popularity: float
    poster_path: str
    production_companies: list[ProductionCompany]
    production_countries: list[dict[str, str]]
    seasons: list[Season]
    next_episode_to_air: str | None = None
