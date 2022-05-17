import os
import time
from collect_bangumi_info import CollectRSS
from auto_set_rule import SetRule
from rename_qb import QbittorrentRename
import json

#sleep_time = os.environ["TIME"]

if __name__ == "__main__":
    while True:
        with open("../config/config.json") as f:
            config = json.load(f)
        with open("../config/bangumi.json") as f:
            info = json.load(f)
        CollectRSS(config, info).run()
        SetRule(config, info).run()
        QbittorrentRename(config).run()
        time.sleep(1800)
