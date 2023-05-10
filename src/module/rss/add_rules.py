from module.database import BangumiDatabase
from module.downloader import DownloadClient


def add_rules():
    with BangumiDatabase() as db:
        bangumi_list = db.not_added()
        if bangumi_list:
            with DownloadClient() as client:
                client.set_rules(bangumi_list)
            db.update_list(bangumi_list)
