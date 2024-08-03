from pathlib import Path

from .config import VERSION, settings
from .log import LOG_PATH, setup_logger
from .search_provider import SEARCH_CONFIG

TMDB_API = "291237f90b24267380d6176c98f7619f"
DATA_PATH = "sqlite:///data/data.db"
LEGACY_DATA_PATH = Path("data/data.json")
VERSION_PATH = Path("config/version.info")
POSTERS_PATH = Path("data/posters")

PLATFORM = "Windows" if "\\" in settings.downloader.path else "Unix"

__all__ = [
    "VERSION",
    "TMDB_API",
    "DATA_PATH",
    "LEGACY_DATA_PATH",
    "VERSION_PATH",
    "POSTERS_PATH",
    "SEARCH_CONFIG",
    "LOG_PATH",
    "PLATFORM",
    "setup_logger",
    "settings",
]
