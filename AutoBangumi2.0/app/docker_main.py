import os
import time
from collect_bangumi_info import CollectRSS
from auto_set_rule import SetRule
from rename_qb import QbittorrentRename
import json


config_path = "/config/config.json"
info_path = "/config/bangumi.json"
host_ip = os.environ["HOST"]
sleep_time = os.environ["TIME"]
user_name = os.environ["USER"]
password = os.environ["PASSWORD"]
rss_link = os.environ["RSS"]
download_path = os.environ["DOWNLOAD_PATH"]
method = os.environ["METHOD"]


def create_config():
    if not os.path.exists(config_path):
        config = {
            "host_ip": host_ip,
            "user_name": user_name,
            "password": password,
            "method": method,
            "rss_link": rss_link,
            "download_path": download_path
        }
        with open(config_path, "w") as c:
            json.dump(config, c, indent=4, separators=(',', ': '), ensure_ascii=False)
    if not os.path.exists(info_path):
        bangumi_info = []
        with open(info_path, "w") as i:
            json.dump(bangumi_info, i, indent=4, separators=(',', ': '), ensure_ascii=False)


if __name__ == "__main__":
    create_config()
    with open(config_path) as f:
        config = json.load(f)
    while True:
        with open(info_path) as f:
            info = json.load(f)
        CollectRSS(config, info).run()
        SetRule(config, info).run()
        QbittorrentRename(config).run()
        time.sleep(float(sleep_time))
