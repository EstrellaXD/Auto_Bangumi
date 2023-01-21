# -*- encoding: utf-8 -*-

DEFAULT_SETTINGS = {
    "data_version": 4.0,
    "host_ip": "localhost:8080",
    "sleep_time": 7200,
    "times": 20,
    "user_name": "admin",
    "password": "adminadmin",
    "download_path": "/downloads/Bangumi/",
    "method": "pn",
    "enable_group_tag": False,
    "info_path": "/config/bangumi.json",
    "not_contain": r"720|\d+-\d+",
    "connect_retry_interval": 5,
    "rule_name_re": r"\:|\/|\.",
    "debug_mode": False,
    "remove_bad_torrent": False,
    "dev_debug": False,
    "eps_complete": False,
    "webui_port": 7892,
    "language": "zh",
    "tmdb_api": "32b19d6a05b512190a056fa4e747cbbc",
    "enable_tmdb": False,
    "socks": None,
    "enable_rss_collector": True,
    "enable_rename": True,
    "reset_folder": False,
    "log_path": "/config/log.txt",
    "refresh_rss": False,
}

ENV_TO_ATTR = {
    "AB_DOWNLOADER_HOST": "host_ip",
    "AB_INTERVAL_TIME": ("sleep_time", lambda e: float(e)),
    "AB_RENAME_FREQ": ("times", lambda e: float(e)),
    "AB_DOWNLOADER_USERNAME": "user_name",
    "AB_DOWNLOADER_PASSWORD": "password",
    "AB_RSS": "rss_link",
    "AB_DOWNLOAD_PATH": "download_path",
    "AB_METHOD": "method",
    "AB_GROUP_TAG": ("enable_group_tag", lambda e: e.lower() in ("true", "1", "t")),
    "AB_NOT_CONTAIN": "not_contain",
    "AB_DEBUG_MODE": ("debug_mode", lambda e: e.lower() in ("true", "1", "t")),
    "AB_EP_COMPLETE": (
        "eps_complete",
        lambda e: e.lower() in ("true", "1", "t")
    ),
    "AB_REMOVE_BAD_BT": ("remove_bad_torrent", lambda e: e.lower() in ("true", "1", "t")),
    "AB_WEBUI_PORT": ("webui_port", lambda e: int(e)),
    "AB_HTTP_PROXY": "http_proxy",
    "AB_LANGUAGE": "language",
    "AB_ENABLE_TMDB": ("enable_tmdb", lambda e: e.lower() in ("true", "1", "t")),
    "AB_SOCKS": "socks",
    "AB_RENAME": ("enable_rename", lambda e: e.lower() in ("true", "1", "t")),
    "AB_RSS_COLLECTOR": ("enable_rss_collector", lambda e: e.lower() in ("true", "1", "t")),
    "AB_RESET_FOLDER": ("reset_folder", lambda e: e.lower() in ("true", "1", "t")),
    "AB_REFRESH_RSS": ("refresh_rss", lambda e: e.lower() in ("true", "1", "t")),
}

DOWNLOADER_DEFAULT = {
    "Host": "localhost:8080",
    "Username": "admin",
    "Password": "adminadmin",
    "DownloadPath": "/downloads/Bangumi/",
    "Filter": r"720|\d+-\d+/",
}

DOWNLOADER_ENV ={
    "AB_DOWNLOADER_HOST": "Host",
    "AB_DOWNLOADER_USERNAME": "Username",
    "AB_DOWNLOADER_PASSWORD": "Password",
    "AB_DOWNLOAD_PATH": "DownloadPath",
    "AB_NOT_CONTAIN": "Filter"
}

DEFAULT_ENV = {
    "AB_INTERVAL_TIME": "SleepTime",
    "AB_RENAME_FREQ": "RenameFreq",
    "AB_RSS_COLLECTOR": "EnableParser",
    "AB_RENAME": "EnableRenamer",
    "AB_EP_COMPLETE": "SeasonCollect",
}

DEFAULT_DEFAULT = {
    "SleepTime": 7200,
    "RenameFreq": 20,
    "EnableParser": True,
    "EnableRenamer": True,
    "SeasonCollect": False,
}


PARSER_ENV = {
    "AB_RSS": "URL",
    "AB_NOT_CONTAIN": "Filter",
    "AB_LANGUAGE": "Language",
}

PARSER_DEFAULT = {
    "URL": "",
    "Filter": r"720|\d+-\d+/",
    "Language": "zh",
}

TMDB_ENV = {
    "AB_ENABLE_TMDB": "EnableTMDB",
    "AB_LANGUAGE": "Language",
}

TMDB_DEFAULT = {
    "EnableTMDB": False,
    "Language": "zh",
}


RENAME_ENV = {
    "AB_METHOD": "RenameMethod",
}

RENAME_DEFAULT = {
    "RenameMethod": "pn",
}

NETWORK_ENV = {
    "AB_WEBUI_PORT": "WebUIPort",
    "AB_HTTP_PROXY": "HTTPProxy",
    "AB_SOCKS": "Socks",
}

NETWORK_DEFAULT = {
    "WebUIPort": 7892,
    "HTTPProxy": "",
    "Socks": "",
}

ENV_DICT = {
    "DEFAULT": DEFAULT_ENV,
    "DOWNLOADER": DOWNLOADER_ENV,
    "PARSER": PARSER_ENV,
    "TMDB": TMDB_ENV,
    "RENAME": RENAME_ENV,
    "NETWORK": NETWORK_ENV,
}

DEFAULT_DICT = {
    "DEFAULT": DEFAULT_DEFAULT,
    "DOWNLOADER": DOWNLOADER_DEFAULT,
    "PARSER": PARSER_DEFAULT,
    "TMDB": TMDB_DEFAULT,
    "RENAME": RENAME_DEFAULT,
    "NETWORK": NETWORK_DEFAULT,
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
