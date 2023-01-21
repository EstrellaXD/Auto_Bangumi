from pydantic import BaseSettings
from configparser import ConfigParser
import os

from .const import ENV_DICT, DEFAULT_DICT

config = ConfigParser()


def get_attr_from_env(env_dict: dict, default_dict: dict):
    """Transforms env-strings to python."""
    conf = {
        attr if isinstance(attr, str) else attr[0]: os.environ[env]
        for env, attr in env_dict.items()
        if env in os.environ
    }
    for key, value in default_dict.items():
        if key not in conf:
            conf[key] = value
    return conf


def init_config():
    for section, env_dict in ENV_DICT.items():
        config[section] = get_attr_from_env(env_dict, DEFAULT_DICT[section])
    with open("config/config.ini", "w") as f:
        config.write(f)


if os.path.isfile("config/config_dev.ini"):
    config.read("config/config_dev.ini")
elif os.path.isfile("config/config.ini"):
    config.read("config/config.ini")
else:
    init_config()


class Setting(BaseSettings):
    DEFAULT = config["DEFAULT"]
    DOWNLOADER = config["DOWNLOADER"]
    PARSER = config["PARSER"]
    RENAME = config["RENAME"]
    NETWORK = config["NETWORK"]


settings = Setting()
