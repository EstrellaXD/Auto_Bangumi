import json
import os

from dataclasses import dataclass

from .const import DEFAULT_SETTINGS, ENV_TO_ATTR



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
        if isinstance(path, dict):
            conf = DEFAULT_SETTINGS
        elif os.path.isfile(path):
            with open(path, "r") as f:
                conf = json.load(f)
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
        settings = DEFAULT_SETTINGS
        for key, section in ENV_TO_ATTR.items():
            for env, attr in section.items():
                if env in os.environ:
                    attr_name = attr[0] if isinstance(attr, tuple) else attr
                    settings[key][attr_name] = self._val_from_env(env, attr)
        with open(CONFIG_PATH, "w") as f:
            json.dump(settings, f, indent=4)
        return settings

try:
    from .version import VERSION
    if os.path.isdir("config"):
        CONFIG_PATH = "config/config.json"
    else:
        CONFIG_PATH = None
except ImportError:
    VERSION = "DEV_VERSION"
    CONFIG_PATH = "config/config_dev.json"

settings = Settings(CONFIG_PATH)


