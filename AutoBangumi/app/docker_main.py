import os
import time
from collect_bangumi_info import CollectRSS
from auto_set_rule import SetRule
from rename_qb import qBittorrentRename
import json
from env import EnvInfo


def create_data_file():
    if not os.path.exists(EnvInfo.info_path):
        bangumi_info = {"rss_link": "",
                        "bangumi_info": []
        }
        with open(EnvInfo.info_path, "w") as i:
            json.dump(bangumi_info, i, indent=4, separators=(',', ': '), ensure_ascii=False)


if __name__ == "__main__":
    create_data_file()
    SetRule().rss_feed()
    while True:
        CollectRSS().run()
        SetRule().run()
        qBittorrentRename().run()
        time.sleep(EnvInfo.sleep_time)
