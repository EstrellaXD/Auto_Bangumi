import os
import time


class EnvInfo:
    info_path = "/config/bangumi.json"
    host_ip = os.environ["HOST"]
    sleep_time = float(os.environ["TIME"])
    user_name = os.environ["USER"]
    password = os.environ["PASSWORD"]
    rss_link = os.environ["RSS"]
    download_path = os.environ["DOWNLOAD_PATH"]
    method = os.environ["METHOD"]
    # rss_link = "https://mikanani.me/RSS/Classic"
    rule_url = "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi/app/rule.json"
    rule_path = "/app/rule.json"
    time_show_obj = time.strftime('%Y-%m-%d %X')