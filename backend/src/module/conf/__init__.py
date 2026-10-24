import sys
from pathlib import Path

from .config import IMAGE_VERSION, VERSION, settings
from .log import LOG_PATH, setup_logger

TMDB_API = "32b19d6a05b512190a056fa4e747cbbc"
DATA_PATH = "sqlite:///data/data.db"
LEGACY_DATA_PATH = Path("data/data.json")
# 3.x 只比较 version.info 末行的 minor，读到 4.x 会当成 3.0 并重建数据库，
# 所以 4.x 另写一份记录，version.info 保持 3.x 的最后状态，回退时仍安全。
VERSION_PATH = Path("config/version_v4.info")
V3_VERSION_PATH = Path("config/version.info")
POSTERS_PATH = Path("data/posters")

PLATFORM = "Windows" if sys.platform == "win32" else "Unix"
