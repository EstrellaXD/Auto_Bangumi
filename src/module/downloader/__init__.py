from module.models import Config


def getClient(settings: Config):
    # TODO 多下载器支持
    type = settings.downloader.type
    host = settings.downloader.host
    username = settings.downloader.username
    password = settings.downloader.password
    ssl = settings.downloader.ssl
    if type == "qbittorrent":
        from module.downloader.client.qb_downloader import QbDownloader

        return QbDownloader(host, username, password, ssl)
    else:
        raise Exception(f"Unsupported downloader type: {type}")
