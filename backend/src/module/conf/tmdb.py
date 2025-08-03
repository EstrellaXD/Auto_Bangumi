"""TMDB API configuration and constants."""

from . import TMDB_API

TMDB_URL = "https://api.themoviedb.org"
TMDB_IMG_URL = "https://image.tmdb.org/t/p/w780"

LANGUAGE = {"zh": "zh-CN", "jp": "ja-JP", "en": "en-US"}


def search_url(keyword: str) -> str:
    """Generate TMDB search URL for TV shows."""
    return f"{TMDB_URL}/3/search/tv?api_key={TMDB_API}&page=1&query={keyword}&include_adult=false"


def info_url(show_id: str, language: str) -> str:
    """Generate TMDB info URL for a specific TV show."""
    return f"{TMDB_URL}/3/tv/{show_id}?api_key={TMDB_API}&language={LANGUAGE[language]}"
