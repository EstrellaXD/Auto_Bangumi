from enum import Enum


class Status(Enum):
    AuthFailed = -1,
    Success = 0,
    UnsupportedDownloaderType = 1,
    AddedCategory = 2,
    NoTorrentFound = 3,
    TorrentAddedBefore = 4,
