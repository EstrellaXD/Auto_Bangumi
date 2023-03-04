from module.conf import settings


def getClient():
    host = settings.downloader.host
    username = settings.downloader.username
    password = settings.downloader.password
    # TODO 多下载器支持
    # 从 settings 里读取下载器名称，然后返回对应 Client
    from module.downloader.qb_downloader import QbDownloader
    return QbDownloader(host, username, password)