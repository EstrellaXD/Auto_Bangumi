import os
import time
from collect_bangumi_info import CollectRSS
from auto_set_rule import SetRule
from rename_qb import qBittorrentRename
import json


class EnvInfo:
    info_path = "/config/bangumi.json"
    host_ip = os.environ["HOST"]
    sleep_time = float(os.environ["TIME"])
    user_name = os.environ["USER"]
    password = os.environ["PASSWORD"]
    rss_link = os.environ["RSS"]
    download_path = os.environ["DOWNLOAD_PATH"]
    method = os.environ["METHOD"]
    rule_url = "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi2.0/app/rule.json"
    rule_path = "/app/rule.json"
    time_show_obj = time.strftime('%Y-%m-%d %X')


def create_data_file():
    if not os.path.exists(EnvInfo.info_path):
        bangumi_info = []
        with open(EnvInfo.info_path, "w") as i:
            json.dump(bangumi_info, i, indent=4, separators=(',', ': '), ensure_ascii=False)


if __name__ == "__main__":
    create_data_file()
    while True:
        CollectRSS().run()
        SetRule().run()
        qBittorrentRename().run()
        time.sleep(EnvInfo.sleep_time)
