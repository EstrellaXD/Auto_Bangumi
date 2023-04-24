import json
import os
import logging

from .const import ENV_TO_ATTR
from module.models import Config

logger = logging.getLogger(__name__)

try:
    from ..__version__ import VERSION
except ImportError:
    logger.info("Can't find version info, use DEV_VERSION instead")
    VERSION = "DEV_VERSION"


class Setting(Config):
    @staticmethod
    def reload():
        load_config_from_file(CONFIG_PATH)


def save_config_to_file(config: Config, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    logger.info(f"Config saved")


def load_config_from_file(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return Setting(**config)


def _val_from_env(env: str, attr: tuple):
    if isinstance(attr, tuple):
        if attr[1] == "bool":
            return os.environ[env].lower() == "true"
        elif attr[1] == "int":
            return int(os.environ[env])
        elif attr[1] == "float":
            return float(os.environ[env])
        else:
            return os.environ[env]
    else:
        return os.environ[env]


def env_to_config() -> Setting:
    _settings = Setting()
    for key, section in ENV_TO_ATTR.items():
        for env, attr in section.items():
            if env in os.environ:
                attr_name = attr[0] if isinstance(attr, tuple) else attr
                setattr(_settings, attr_name, _val_from_env(env, attr))
    return _settings


if os.path.isdir("config") and VERSION == "DEV_VERSION":
    CONFIG_PATH = "config/config_dev.json"
    if os.path.isfile(CONFIG_PATH):
        settings = load_config_from_file(CONFIG_PATH)
    else:
        settings = env_to_config()
        save_config_to_file(settings, CONFIG_PATH)
elif os.path.isdir("config") and VERSION != "DEV_VERSION":
    CONFIG_PATH = "config/config.json"
    if os.path.isfile(CONFIG_PATH):
        settings = load_config_from_file(CONFIG_PATH)
    else:
        settings = env_to_config()
        save_config_to_file(settings, CONFIG_PATH)
else:
    settings = Setting()




