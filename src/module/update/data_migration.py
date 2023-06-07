import os

from module.database import BangumiDatabase
from module.models import BangumiData
from module.utils import json_config


def data_migration():
    if not os.path.isfile("data/data.json"):
        return False
    old_data = json_config.load("data/data.json")
    infos = old_data["bangumi_info"]
    rss_link = old_data["rss_link"]
    new_data = []
    for info in infos:
        new_data.append(BangumiData(**info, rss_link=[rss_link]))
    with BangumiDatabase() as database:
        database.update_table()
        database.insert_list(new_data)
    os.remove("data/data.json")
