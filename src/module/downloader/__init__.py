def getClient():
    # TODO 多下载器支持
    # 从 settings 里读取下载器名称，然后返回对应 Client
    from .qb_downloader import QbDownloader
    return QbDownloader()
