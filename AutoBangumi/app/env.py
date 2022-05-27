import os
import time


class EnvInfo:
    debug_mode = True
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
        not_contain = os.environ["NOT_CONTAIN"]
        get_rule_debug = os.getenv("RULE_DEBUG", 'False').lower() in ('true', '1', 't')
    else:
        # Debug ENV
        host_ip = "localhost:8181"
        sleep_time = 10
        user_name = "admin"
        password = "adminadmin"
        rss_link = "https://mikanani.me/RSS/classic"
        download_path = "/downloads/Bangumi"
        method = "pn"
        enable_group_tag = True
        info_path = "../config/bangumi.json"
        rule_path = "../config/rule.json"
        not_contain = "720"
        get_rule_debug = True
    # Static ENV
    rule_url = "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi/config/rule.json"
    time_show_obj = time.strftime('%Y-%m-%d %X')
    rule_name_re = r"\:|\/|\."


class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
