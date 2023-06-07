from .config import VERSION, settings
from .log import LOG_PATH, setup_logger

TMDB_API = "32b19d6a05b512190a056fa4e747cbbc"
DATA_PATH = "data/data.db"

PLATFORM = "Windows" if "\\" in settings.downloader.path else "Unix"
