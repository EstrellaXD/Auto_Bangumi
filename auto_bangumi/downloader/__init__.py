from conf import settings


def getClient():
    host = settings.host_ip
    username = settings.user_name
    password = settings.password
    # TODO 多下载器支持
    # 从 settings 里读取下载器名称，然后返回对应 Client
    from downloader.qb_downloader import QbDownloader
    return QbDownloader(host, username, password)