import sys

from .search_provider import SEARCH_CONFIG
from version import APP_VERSION

PLATFORM = sys.platform


__all__ = [
    "SEARCH_CONFIG",
    "PLATFORM",
    "APP_VERSION",
]
