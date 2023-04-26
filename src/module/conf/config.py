import json
import os
import logging
from dotenv import load_dotenv

from module.conf.const import ENV_TO_ATTR
from module.models.config import Config

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
    config_dict = config.dict()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=4)
    logger.info(f"Config saved")


def load_config_from_file(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return Setting(**config)


def _val_from_env(env: str, attr: tuple):
    if isinstance(attr, tuple):
        conv_func = attr[1]
        return conv_func(os.environ[env])
    else:
        return os.environ[env]


def env_to_config() -> Setting:
    _settings = Setting().dict()
    for key, section in ENV_TO_ATTR.items():
        for env, attr in section.items():
            if env in os.environ:
                if isinstance(attr, list):
                    for _attr in attr:
                        attr_name = _attr[0] if isinstance(_attr, tuple) else _attr
                        _settings[key][attr_name] = _val_from_env(env, _attr)
                else:
                    attr_name = attr[0] if isinstance(attr, tuple) else attr
                    _settings[key][attr_name] = _val_from_env(env, attr)
    return Setting(**_settings)


if os.path.isdir("config") and VERSION == "DEV_VERSION":
    CONFIG_PATH = "config/config_dev.json"
    if os.path.isfile(CONFIG_PATH):
        settings = load_config_from_file(CONFIG_PATH)
    else:
        load_dotenv(".env")
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




