import os
import time
from collect_bangumi_info import CollectRSS
from auto_set_rule import SetRule
from rename_qb import QbittorrentRename
import json


config_path = "/config/config.json"
info_path = "/config/bangumi.json"
sleep_time = os.environ["TIME"]


def create_config():
    if not os.path.exists(config_path):
        config = {
            "host_ip": "192.168.31.10:8181",
            "user_name": "admin",
            "password": "adminadmin",
            "method": "pn",
            "rss_link": "https://mikanani.me/RSS/MyBangumi?token=qTxKo48gH1SrFNy8X%2fCfQUoeElNsgKNWFNzNieKwBH8%3d",
            "download_path": "/downloads/Bangumi"
        }
        with open(config_path,"w") as c:
            json.dump(config, c, indent=4, separators=(',', ': '), ensure_ascii=False)
    if not os.path.exists(info_path):
        bangumi_info = [{"title":"simple","season":""}]
        with open(info_path) as i:
            json.dump(bangumi_info, i, indent=4, separators=(',', ': '), ensure_ascii=False)
    print(f"[{time.strftime('%X')}]   请填入配置参数")
    quit()


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
