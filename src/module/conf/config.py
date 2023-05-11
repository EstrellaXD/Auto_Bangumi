import json
import os
import logging
from dotenv import load_dotenv

from .const import ENV_TO_ATTR
from module.models.config import Config

logger = logging.getLogger(__name__)

try:
    from module.__version__ import VERSION

    if VERSION == "DEV_VERSION":
        logger.info("Can't find version info, use DEV_VERSION instead")
        CONFIG_PATH = "config/config_dev.json"
    else:
        CONFIG_PATH = f"config/config.json"
except ImportError:
    logger.info("Can't find version info, use DEV_VERSION instead")
    VERSION = "DEV_VERSION"
    CONFIG_PATH = "config/config_dev.json"


class Settings(Config):
    def __init__(self):
        super().__init__()
        if os.path.exists(CONFIG_PATH):
            self.load()
            self.save()
        else:
            # load from env
            load_dotenv(".env")
            self.__load_from_env()
            self.save()

    def load(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        config_obj = Config.parse_obj(config)
        self.__dict__.update(config_obj.__dict__)
        logger.info(f"Config loaded")

    def save(self, config_dict: dict | None = None):
        if not config_dict:
            config_dict = self.dict()
        if not os.path.exists("config"):
            os.makedirs("config")
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4)

    def rss_link(self):
        if "://" not in self.rss_parser.custom_url:
            return f"https://{self.rss_parser.custom_url}/RSS/MyBangumi?token={self.rss_parser.token}"
        return (
            f"{self.rss_parser.custom_url}/RSS/MyBangumi?token={self.rss_parser.token}"
        )

    def __load_from_env(self):
        config_dict = self.dict()
        for key, section in ENV_TO_ATTR.items():
            for env, attr in section.items():
                if env in os.environ:
                    if isinstance(attr, list):
                        for _attr in attr:
                            attr_name = _attr[0] if isinstance(_attr, tuple) else _attr
                            config_dict[key][attr_name] = self.__val_from_env(
                                env, _attr
                            )
                    else:
                        attr_name = attr[0] if isinstance(attr, tuple) else attr
                        config_dict[key][attr_name] = self.__val_from_env(env, attr)
        config_obj = Config.parse_obj(config_dict)
        self.__dict__.update(config_obj.__dict__)
        logger.info(f"Config loaded from env")

    @staticmethod
    def __val_from_env(env: str, attr: tuple):
        if isinstance(attr, tuple):
            conv_func = attr[1]
            return conv_func(os.environ[env])
        else:
            return os.environ[env]


settings = Settings()
