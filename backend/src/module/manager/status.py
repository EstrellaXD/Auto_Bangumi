from enum import Enum


class Status(Enum):
    AuthFailed = -1,  # This status is used to present that qBittorrent is not authed.
    Success = 0,  # Normal state, put it to 0.
    UnsupportedDownloaderType = 1,  # Unsupported downloader type, may be used in the future while multiple
    # downloader is implemented.
    AddedCategory = 2,              # This shows that the category (the anime file) is already created.
    NoTorrentFound = 3,             # This presents that no torrent file can be found.
    TorrentAddedBefore = 4,         # This presents that the given torrent files were added before. 
