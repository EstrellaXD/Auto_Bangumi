import sys
from pathlib import Path

from .config import VERSION, get_plugin_config, settings
from .log import LOG_PATH, setup_logger
from .search_provider import SEARCH_CONFIG
from .tmdb import TMDB_API_KEY

PLATFORM = sys.platform
DATA_PATH = "sqlite:///data/data.db"
LEGACY_DATA_PATH = Path("data/data.json")
VERSION_PATH = Path("config/version.info")
POSTERS_PATH = Path("data/posters")


__all__ = [
    "VERSION",
    "TMDB_API_KEY",
    "DATA_PATH",
    "LEGACY_DATA_PATH",
    "VERSION_PATH",
    "POSTERS_PATH",
    "SEARCH_CONFIG",
    "LOG_PATH",
    "PLATFORM",
    "setup_logger",
    "settings",
    "get_plugin_config",
]
