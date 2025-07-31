from typing import TypedDict
from dataclasses import dataclass


class ShowInfo(TypedDict):
    adult: bool
    backdrop_path: str
    genre_ids: list[int]
    id: int
    origin_country: list[str]
    original_language: str
    original_name: str
    overview: str
    popularity: float
    poster_path: str
    first_air_date: str
    name: str
    vote_average: float
    vote_count: int


class Genre(TypedDict):
    id: int
    name: str


class Network(TypedDict):
    id: int
    logo_path: str | None
    name: str
    origin_country: str


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


class ProductionCompany(TypedDict):
    id: int
    name: str
    origin_country: str
    logo_path: str


class Season(TypedDict):
    air_date: str | None
    episode_count: int
    id: int
    name: str
    overview: str
    season_number: int
    vote_average: float
    poster_path: str


class TVShow(TypedDict):
    adult: bool
    backdrop_path: str
    # 不知道是什么类型, 都是[]
    created_by: list[str]
    episode_run_time: list[int]
    # 就像是"2024-04-12"
    first_air_date: str
    genres: list[Genre]
    homepage: str
    id: int
    in_production: bool
    languages: list[str]
    last_air_date: str
    last_episode_to_air: str
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
    next_episode_to_air: str


@dataclass
class TMDBInfo:
    id: int
    title: str
    original_title: str
    season: int
    last_season: int
    year: str
    poster_link: str = ""