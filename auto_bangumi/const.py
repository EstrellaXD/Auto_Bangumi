# -*- encoding: utf-8 -*-

DEFAULT_SETTINGS = {
    "host_ip": "localhost:8181",
    "sleep_time": 1800,
    "user_name": "admin",
    "password": "adminadmin",
    "download_path": "",
    "method": "pn",
    "enable_group_tag": False,
    "info_path": "/config/bangumi.json",
    "anidb_path": "/config/anidb.json",
    "anidb_url": "https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi_resourse/main/resource/season_data.json",
    "not_contain": "720",
    "rule_name_re": r"\:|\/|\.",
    "connect_retry_interval": 5,
    "debug_mode": False,
    "season_one_tag": True,
    "remove_bad_torrent": False,
    "dev_debug": False,
    "data_version": 4.0,
    "enable_eps_complete": False,
    "first_sleep": 600,
    "webui_port": 7892,
    "enable_fuzz_match": True
}

ENV_TO_ATTR = {
    "AB_DOWNLOADER_HOST": "host_ip",
    "AB_INTERVAL_TIME": ("sleep_time", lambda e: float(e)),
    "AB_DOWNLOADER_USERNAME": "user_name",
    "AB_DOWNLOADER_PASSWORD": "password",
    "AB_RSS": "rss_link",
    "AB_DOWNLOAD_PATH": "download_path",
    "AB_METHOD": "method",
    "AB_GROUP_TAG": ("enable_group_tag", lambda e: e.lower() in ("true", "1", "t")),
    "AB_NOT_CONTAIN": "not_contain",
    "AB_DEBUG_MODE": ("debug_mode", lambda e: e.lower() in ("true", "1", "t")),
    "AB_EP_COMPLETE": (
        "enable_eps_complete",
        lambda e: e.lower() in ("true", "1", "t")
    ),
    "AB_SEASON_ONE": ("season_one_tag", lambda e: e.lower() in ("true", "1", "t")),
    "AB_REMOVE_BAD_BT": ("remove_bad_torrent", lambda e: e.lower() in ("true", "1", "t")),
    "AB_FIRST_SLEEP": ("first_sleep", lambda e: float(e)),
    "AB_WEBUI_PORT": ("webui_port", lambda e: int(e)),
    "AB_FUZZ_MATCH": ("enable_fuzz_match", lambda e: e.lower() in ("true", "1", "t"))
}


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
