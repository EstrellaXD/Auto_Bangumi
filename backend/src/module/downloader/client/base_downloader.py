from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from models import TorrentDownloadInfo
    from models.config import Downloader as DownloaderConfig

# 主要实现以下 个功能
# 1. renamer,用以实现重命名功能 hash, old name, new name
# 2. move, 用以实现改数据后的转移
# 3. add, 用以加种子
# 4. get_info, 获取当前所有的有关种子
# 5. auth, 用以登陆
# 6. check_host, 用以检查连通性
# 7. logout,用以登出
#
class BaseDownloader(metaclass=ABCMeta):
    def __init__(self):
        self.api_interval: float = 0.2

    @abstractmethod
    def initialize(self,config:DownloaderConfig) -> None:
        """初始化下载器"""
        pass

    @abstractmethod
    async def auth(self) -> bool:
        pass

    @abstractmethod
    async def check_host(self) -> bool:
        pass

    @abstractmethod
    async def logout(self) -> bool:
        pass

    @abstractmethod
    async def get_torrent_files(self, hash) -> list[str]:
        pass

    @abstractmethod
    async def torrents_info(self, status_filter, category, tag, limit) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def torrent_info(self, hash: str) -> TorrentDownloadInfo | None:
        pass

    @abstractmethod
    async def rename(self, torrent_hash: str, old_path: str, new_path: str) -> bool:
        pass

    @abstractmethod
    async def move(self, hashes: str, new_location: str) -> bool:
        pass

    @abstractmethod
    async def add(self, hashs:list[str], torrent_content:bytes|None, save_path) -> list[str] :
        pass

    @abstractmethod
    async def delete(self, hashes: list[str] | str) -> bool:
        pass
