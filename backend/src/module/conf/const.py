# -*- encoding: utf-8 -*-
from typing import Any

# ENV_TO_ATTR: maps AB_* environment variables to Config model attribute paths.
#   Values are either a string attr name, a (attr_name, converter) tuple, or a
#   list of such tuples when a single env var sets multiple attributes.
ENV_TO_ATTR: dict[str, dict[str, Any]] = {
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
        "AB_RSS_PARSER_ENGINE": ("engine", lambda e: e.lower()),
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
        "AB_REVISION_CONFLICT_POLICY": (
            "revision_conflict_policy",
            lambda e: e.lower(),
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
            ("type", lambda e: "socks5"),
            ("host", lambda e: e.split(",")[0]),
            ("port", lambda e: int(e.split(",")[1])),
            ("username", lambda e: e.split(",")[2]),
            ("password", lambda e: e.split(",")[3]),
        ],
    },
}
