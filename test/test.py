import json
import os

config_path = "config.json"
info_path = "bangumi.json"


def create_config():
    if not os.path.exists(config_path):
        config = {
            "host_ip": "127.0.0.1:8080",
            "user_name": "admin",
            "password": "adminadmin",
            "method": "pn",
            "rss_link": "https://mikanani.me/RSS/MyBangumi?token=qTxKo48gH1SrFNy8X%2fCfQUoeElNsgKNWFNzNieKwBH8%3d",
            "download_path": "/downloads/Bangumi"
        }
        with open(config_path,"w") as c:
            json.dump(config, c, indent=4, separators=(',', ': '), ensure_ascii=False)
    if not os.path.exists(info_path):
        bangumi_info = [{"title": "simple","season": ""}]
        with open(info_path, "w") as i:
            json.dump(bangumi_info, i, indent=4, separators=(',', ': '), ensure_ascii=False)
    print("请填入配置参数")
    quit()

create_config()