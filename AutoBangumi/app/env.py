import os
import time


class EnvInfo:
    debug_mode = False
    # Docker Env
    if not debug_mode:
        host_ip = os.environ["HOST"]
        sleep_time = float(os.environ["TIME"])
        user_name = os.environ["USER"]
        password = os.environ["PASSWORD"]
        rss_link = os.environ["RSS"]
        download_path = os.environ["DOWNLOAD_PATH"]
        method = os.environ["METHOD"]
        enable_group_tag = os.getenv("GROUP_TAG", 'False').lower() in ('true', '1', 't')
        info_path = "/config/bangumi.json"
        rule_path = "/config/rule.json"
    else:
        # Debug ENV
        host_ip = "localhost:8080"
        sleep_time = 10
        user_name = "admin"
        password = "adminadmin"
        rss_link = ""
        download_path = "/downloads/Bangumi"
        method = "pn"
        enable_group_tag = True
        info_path = "../config/bangumi.json"
        rule_path = "../config/rule.json"
    # Static ENV
    rule_url = "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi/config/rule.json"
    time_show_obj = time.strftime('%Y-%m-%d %X')
    rule_name_re = r"\:|\/|\."
