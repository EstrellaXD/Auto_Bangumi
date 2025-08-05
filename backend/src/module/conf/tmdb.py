"""TMDB API configuration and constants."""

from .config import settings


TMDB_URL = "https://api.themoviedb.org"
TMDB_IMG_URL = "https://image.tmdb.org/t/p/w780"

# Default TMDB API key, replace with your own key if needed
# Note: Using a public key is not recommended for production use.
# It is better to set your own key in the configuration.
TMDB_API_KEY = "291237f90b24267380d6176c98f7619f"

LANGUAGE = {"zh": "zh-CN", "jp": "ja-JP", "en": "en-US"}

def get_api_key():
    """Get the TMDB API key from settings."""
    return settings.rss_parser.tmdb_api_key or TMDB_API_KEY


def search_url(keyword: str) -> str:
    """Generate TMDB search URL for TV shows."""
    return f"{TMDB_URL}/3/search/tv?api_key={get_api_key()}&page=1&query={keyword}&include_adult=false"


def info_url(show_id: str, language: str) -> str:
    """Generate TMDB info URL for a specific TV show."""
    return f"{TMDB_URL}/3/tv/{show_id}?api_key={get_api_key()}&language={LANGUAGE[language]}"
