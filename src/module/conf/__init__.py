from .log import setup_logger, LOG_PATH
from .config import settings, VERSION


TMDB_API = "32b19d6a05b512190a056fa4e747cbbc"
DATA_PATH = "data/data.json"
RSS_LINK = f"https://{settings.rss_parser.custom_url}/RSS/MyBangumi?token={settings.rss_parser.token}"
