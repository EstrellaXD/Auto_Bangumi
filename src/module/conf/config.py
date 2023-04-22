import json
import os
import logging

from dataclasses import dataclass

from .const import DEFAULT_SETTINGS, ENV_TO_ATTR

logger = logging.getLogger(__name__)

try:
    from ..__version__ import VERSION
except ImportError:
    logger.info("Can't find version info, use DEV_VERSION instead")
    VERSION = "DEV_VERSION"


class ConfLoad(dict):
    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self[key] = value


@dataclass
class Settings:
    program: ConfLoad
    downloader: ConfLoad
    rss_parser: ConfLoad
    bangumi_manage: ConfLoad
    debug: ConfLoad
    proxy: ConfLoad
    notification: ConfLoad

    def __init__(self, path: str | None):
        self.load(path)

    def load(self, path: str | None):
        if path is None:
            conf = DEFAULT_SETTINGS
        elif os.path.isfile(path):
            with open(path, "r") as f:
                # Use utf-8 to avoid encoding error
                conf = json.load(f, encoding="utf-8")
        else:
            conf = self._create_config()
        for key, section in conf.items():
            setattr(self, key, ConfLoad(section))

    @staticmethod
    def _val_from_env(env, attr):
        val = os.environ[env]
        if isinstance(attr, tuple):
            conv_func = attr[1]
            val = conv_func(val)
        return val

    def _create_config(self):
        _settings = DEFAULT_SETTINGS
        for key, section in ENV_TO_ATTR.items():
            for env, attr in section.items():
                if env in os.environ:
                    attr_name = attr[0] if isinstance(attr, tuple) else attr
                    _settings[key][attr_name] = self._val_from_env(env, attr)
        with open(CONFIG_PATH, "w") as f:
            # Save utf-8 to avoid encoding error
            json.dump(_settings, f, indent=4, ensure_ascii=False)
        logger.warning(f"Config file had been transferred from environment variables to {CONFIG_PATH}, some settings may be lost.")
        logger.warning("Please check the config file and restart the program.")
        logger.warning("Please check github wiki (https://github.com/EstrellaXD/Auto_Bangumi/#/wiki) for more information.")
        return _settings


if os.path.isdir("config") and VERSION == "DEV_VERSION":
    CONFIG_PATH = "config/config_dev.json"
elif os.path.isdir("config") and VERSION != "DEV_VERSION":
    CONFIG_PATH = "config/config.json"
else:
    CONFIG_PATH = None

settings = Settings(CONFIG_PATH)


