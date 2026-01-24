# -*- encoding: utf-8 -*-
DEFAULT_SETTINGS = {
    "program": {
        "rss_time": 900,
        "rename_time": 60,
        "webui_port": 7892,
    },
    "downloader": {
        "type": "qbittorrent",
        "host": "172.17.0.1:8080",
        "username": "admin",
        "password": "adminadmin",
        "path": "/downloads/Bangumi",
        "ssl": False,
    },
    "rss_parser": {
        "enable": True,
        "filter": ["720", "\\d+-\\d+"],
        "language": "zh",
    },
    "bangumi_manage": {
        "enable": True,
        "eps_complete": False,
        "rename_method": "pn",
        "group_tag": False,
        "remove_bad_torrent": False,
    },
    "log": {
        "debug_enable": False,
    },
    "proxy": {
        "enable": False,
        "type": "http",
        "host": "",
        "port": 0,
        "username": "",
        "password": "",
    },
    "notification": {"enable": False, "type": "telegram", "token": "", "chat_id": ""},
    "experimental_openai": {
        "enable": False,
        "api_key": "",
        "api_base": "https://api.openai.com/v1",
        "api_type": "openai",
        "api_version": "2023-05-15",
        "model": "gpt-3.5-turbo",
        "deployment_id": "",
    },
}


ENV_TO_ATTR = {
    "program": {
        "AB_INTERVAL_TIME": ("rss_time", lambda e: int(e)),
        "AB_RENAME_FREQ": ("rename_time", lambda e: int(e)),
        "AB_WEBUI_PORT": ("webui_port", lambda e: int(e)),
    },
    "downloader": {
        "AB_DOWNLOADER_HOST": "host",
        "AB_DOWNLOADER_USERNAME": "username",
        "AB_DOWNLOADER_PASSWORD": "password",
        "AB_DOWNLOAD_PATH": "path",
    },
    "rss_parser": {
        "AB_RSS_COLLECTOR": ("enable", lambda e: e.lower() in ("true", "1", "t")),
        "AB_NOT_CONTAIN": ("filter", lambda e: e.split("|")),
        "AB_LANGUAGE": "language",
    },
    "bangumi_manage": {
        "AB_RENAME": ("enable", lambda e: e.lower() in ("true", "1", "t")),
        "AB_METHOD": ("rename_method", lambda e: e.lower()),
        "AB_GROUP_TAG": ("group_tag", lambda e: e.lower() in ("true", "1", "t")),
        "AB_EP_COMPLETE": ("eps_complete", lambda e: e.lower() in ("true", "1", "t")),
        "AB_REMOVE_BAD_BT": (
            "remove_bad_torrent",
            lambda e: e.lower() in ("true", "1", "t"),
        ),
    },
    "log": {
        "AB_DEBUG_MODE": ("debug_enable", lambda e: e.lower() in ("true", "1", "t")),
    },
    "proxy": {
        "AB_HTTP_PROXY": [
            ("enable", lambda e: True),
            ("type", lambda e: "http"),
            ("host", lambda e: e.split(":")[0]),
            ("port", lambda e: int(e.split(":")[1])),
        ],
        "AB_SOCKS": [
            ("enable", lambda e: True),
            ("type", lambda e: "socks"),
            ("host", lambda e: e.split(",")[0]),
            ("port", lambda e: int(e.split(",")[1])),
            ("username", lambda e: e.split(",")[2]),
            ("password", lambda e: e.split(",")[3]),
        ],
    },
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
