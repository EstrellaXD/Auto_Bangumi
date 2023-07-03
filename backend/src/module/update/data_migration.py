import os

from module.conf import LEGACY_DATA_PATH
from module.database import BangumiDatabase
from module.models import BangumiData
from module.utils import json_config


def data_migration():
    if not LEGACY_DATA_PATH.exists():
        return False
    old_data = json_config.load(LEGACY_DATA_PATH)
    infos = old_data["bangumi_info"]
    rss_link = old_data["rss_link"]
    new_data = []
    for info in infos:
        new_data.append(BangumiData(**info, rss_link=[rss_link]))
    with BangumiDatabase() as database:
        database.update_table()
        database.insert_list(new_data)

    LEGACY_DATA_PATH.unlink(missing_ok=True)
