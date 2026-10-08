"""下载器契约的宿主侧入口：定义已移至 ``ab_sdk.downloader``，此处重新导出。"""

from ab_sdk.downloader import (
    AddResult,
    CoreDownloaderClient,
    DownloaderCapabilities,
    DownloaderClient,
    DownloaderConnection,
    DownloaderFactory,
    RenameOutcome,
    RenameResult,
)

__all__ = [
    "AddResult",
    "CoreDownloaderClient",
    "DownloaderCapabilities",
    "DownloaderClient",
    "DownloaderConnection",
    "DownloaderFactory",
    "RenameOutcome",
    "RenameResult",
]
