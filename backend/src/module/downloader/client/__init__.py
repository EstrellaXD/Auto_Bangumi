import importlib
import logging

from module.conf import settings
from module.downloader.client.expection import AuthorizationError

logger = logging.getLogger(__name__)

download_type = settings.downloader.type
package_path = f"module.downloader.client.{download_type}"
downloader = importlib.import_module(package_path)
Downloader = downloader.Downloader
__all__ = ["Downloader", "AuthorizationError"]
