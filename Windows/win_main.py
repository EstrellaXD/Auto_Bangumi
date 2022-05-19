import os
import time
from app.collect_bangumi_info import CollectRSS
from app.auto_set_rule import SetRule
from app.rename_qb import QbittorrentRename
import json


if __name__ == "__main__":
    with open("config/config.json") as f:
        config = json.load(f)
    while True:
        with open("config/bangumi.json") as f:
            info = json.load(f)
        with open("../config/rule.json") as f:
            rule = json.load(f)
        CollectRSS(config, info, rule).run()
        SetRule(config).run()
        QbittorrentRename(config).run()
        time.sleep(float(1800))
