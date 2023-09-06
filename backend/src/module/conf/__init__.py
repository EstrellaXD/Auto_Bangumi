from pathlib import Path

from .config import VERSION, settings
from .log import LOG_PATH, setup_logger
from .search_provider import SEARCH_CONFIG

TMDB_API = "32b19d6a05b512190a056fa4e747cbbc"
DATA_PATH = "sqlite:///data/data.db"
LEGACY_DATA_PATH = Path("data/data.json")
VERSION_PATH = Path("config/version.info")

PLATFORM = "Windows" if "\\" in settings.downloader.path else "Unix"
