# -*- encoding: utf-8 -*-

DEFAULT_SETTINGS = {
    "host_ip": "localhost:8080",
    "sleep_time": 1800,
    "user_name": "admin",
    "password": "adminadmin",
    "rss_link": "https://mikanani.me/RSS/classic",
    "download_path": "/downloads/Bangumi",
    "method": "pn",
    "enable_group_tag": True,
    "info_path": "/config/bangumi.json",
    "rule_path": "/config/rule_beta.json",
    "not_contain": "720",
    "get_rule_debug": False,
    "rule_url": "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi/config/rule.json",
    "rule_name_re": r"\:|\/|\.",
    "connect_retry_interval": 5,
    "debug_mode": True,
    "season_one_tag": True
}

ENV_TO_ATTR = {
    "AB_DOWNLOADER_HOST": "host_ip",
    "AB_INTERVAL_TIME": "sleep_time",
    "AB_DOWNLOADER_USERNAME": "user_name",
    "AB_DOWNLOADER_PASSWORD": "password",
    "AB_RSS": "rss_link",
    "AB_DOWNLOAD_PATH": "download_path",
    "AB_METHOD": "method",
    "AB_GROUP_TAG": "enable_group_tag",
    "AB_NOT_CONTAIN": "not_contain",
    "AB_RULE_DEBUG": "get_rule_debug",
    "AB_DEBUG_MODE": "debug_mode",
    "AB_EP_COMPLETE": "enable_eps_complete",
    "AB_SEASON_ONE": "season_one_tag"
}

FULL_SEASON_SUPPORT_GROUP = ["Lilith-Raws"]


class BCOLORS:
    @staticmethod
    def _(color: str, *args: str) -> str:
        strings = [str(s) for s in args]
        return f"{color}{', '.join(strings)}{BCOLORS.ENDC}"

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
