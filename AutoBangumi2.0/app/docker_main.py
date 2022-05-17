import os
import time
from collect_bangumi_info import CollectRSS
from auto_set_rule import SetRule
from rename_qb import QbittorrentRename
import json
import qbittorrentapi

sleep_time = os.environ["TIME"]

if __name__ == "__main__":
    """qb = qbittorrentapi.Client(username='admin', password='adminadmin', host='192.168.31.10', port=8181)
    try:
        qb.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(e)
    qb.rss_add_feed(url="")"""
    while True:
        with open("/config/config.json") as f:
            config = json.load(f)
        with open("/config/bangumi.json") as f:
            info = json.load(f)
        CollectRSS(config, info).run()
        SetRule(config, info).run()
        QbittorrentRename(config).run()
        time.sleep(float(sleep_time))
