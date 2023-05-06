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
    def __init__(self):
        if VERSION != "DEV_VERSION":
            CONFIG_PATH = "config/config.json"
        else:
            CONFIG_PATH = "config/config_dev.json"
        if os.path.isfile(CONFIG_PATH):
            config = load_config_from_file(CONFIG_PATH)
        else:
            logger.info(f"Can't find config file, use env instead")
            load_dotenv()
            config = env_to_config()
        super().__init__(config)
        save_config_to_file(self, CONFIG_PATH)
        self.reload()
        
    @staticmethod
    def reload():
        load_config_from_file(CONFIG_PATH)

    def save(self):
        save_config_to_file(self, CONFIG_PATH)


def save_config_to_file(config: Config, path: str):
    config_dict = config.dict()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=4)
    logger.info(f"Config saved")


def load_config_from_file(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config


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
    return _settings




