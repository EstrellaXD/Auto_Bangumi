# -*- encoding: utf-8 -*-

from math import fabs


DEFAULT_SETTINGS = {
    "host_ip": "localhost:8080",
    "sleep_time": 1800,
    "user_name": "admin",
    "password": "adminadmin",
    "rss_link": "https://mikanani.me/RSS/classic",
    "download_path": "/downloads/Bangumi",
    "method": "pn",
    "enable_group_tag": True,
    "info_path": "config/bangumi.json",
    "rule_path": "config/rule.json",
    "not_contain": "720",
    "get_rule_debug": False,
    "rule_url": "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi/config/rule.json",
    "rule_name_re": r"\:|\/|\.",
    "connect_retry_interval": 5,
    "enable_eps_complete": False,
}

ENV_TO_ATTR = {
    "HOST": "host_ip",
    "TIME": ("sleep_time", lambda e: float(e)),
    "USER": "user_name",
    "PASSWORD": "password",
    "RSS": "rss_link",
    "DOWNLOAD_PATH": "download_path",
    "METHOD": "method",
    "GROUP_TAG": ("enable_group_tag", lambda e: e.lower() in ("true", "1", "t")),
    "NOT_CONTAIN": "not_contain",
    "RULE_DEBUG": ("get_rule_debug", lambda e: e.lower() in ("true", "1", "t")),
    "EP_COMPLETE": ("enable_eps_complete", lambda e: e.lower() in ("true", "1", "t")),
}

FULL_SEASON_SUPPORT_GROUP = ["Lilith-Raws"]


class BCOLORS:
    @staticmethod
    def _(color: str, string: str) -> str:
        return f"{color}{string}{BCOLORS.ENDC}"

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
