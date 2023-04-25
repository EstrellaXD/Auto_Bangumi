from module.conf import settings


def getClient():
    # TODO 多下载器支持
    # 从 settings 里读取下载器名称，然后返回对应 Client
    if settings.downloader.type == "qbittorrent":
        from .qb_downloader import QbDownloader
        return QbDownloader()
    else:
        raise Exception(f"Unsupported downloader type: {settings.downloader.type}")
