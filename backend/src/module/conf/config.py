import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from module.models.config import Config

from .const import DEFAULT_SETTINGS, ENV_TO_ATTR

logger = logging.getLogger(__name__)
CONFIG_ROOT = Path("config")


try:
    from module.__version__ import VERSION
except ImportError:
    logger.info("Can't find version info, use DEV_VERSION instead")
    VERSION = "DEV_VERSION"

CONFIG_PATH = (
    CONFIG_ROOT / "config_dev.json"
    if VERSION == "DEV_VERSION"
    else CONFIG_ROOT / "config.json"
).resolve()


class Settings(Config):
    """Runtime configuration singleton.

    On construction, loads from ``CONFIG_PATH`` if the file exists (and
    immediately re-saves to apply any migrations), otherwise bootstraps
    defaults from environment variables via ``init()``.

    Use ``settings`` module-level instance rather than instantiating directly.
    """

    def __init__(self):
        super().__init__()
        if CONFIG_PATH.exists():
            self.load()
            self.save()
        else:
            self.init()

    def load(self):
        """Load and validate configuration from ``CONFIG_PATH``, applying migrations."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        config = self._migrate_old_config(config)
        config_obj = Config.model_validate(config)
        self.__dict__.update(config_obj.__dict__)
        logger.info("Config loaded")

    @staticmethod
    def _migrate_old_config(config: dict) -> dict:
        """Migrate old config field names (3.1.x) to current format (3.2.x)."""
        program = config.get("program", {})
        # Rename sleep_time -> rss_time
        if "sleep_time" in program and "rss_time" not in program:
            program["rss_time"] = program.pop("sleep_time")
        elif "sleep_time" in program:
            program.pop("sleep_time")
        # Rename times -> rename_time
        if "times" in program and "rename_time" not in program:
            program["rename_time"] = program.pop("times")
        elif "times" in program:
            program.pop("times")
        # Remove deprecated data_version field
        program.pop("data_version", None)

        # Remove deprecated rss_parser fields
        rss_parser = config.get("rss_parser", {})
        for key in ("type", "custom_url", "token", "enable_tmdb"):
            rss_parser.pop(key, None)

        # Add security section if missing (preserves local-network MCP default)
        if "security" not in config:
            config["security"] = DEFAULT_SETTINGS["security"]

        return config

    def save(self, config_dict: dict | None = None):
        """Write configuration to ``CONFIG_PATH``. Uses current state when no dict supplied."""
        if not config_dict:
            config_dict = self.model_dump()
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)

    def init(self):
        """Bootstrap a new config file from ``.env`` and environment variables."""
        load_dotenv(".env")
        self.__load_from_env()
        self.save()

    def __load_from_env(self):
        """Apply ``ENV_TO_ATTR`` mappings from the process environment to the config dict."""
        config_dict = self.model_dump()
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
        config_obj = Config.model_validate(config_dict)
        self.__dict__.update(config_obj.__dict__)
        logger.info("Config loaded from env")

    @staticmethod
    def __val_from_env(env: str, attr: tuple | str):
        """Return the environment variable value, applying the converter when attr is a tuple."""
        if isinstance(attr, tuple):
            return attr[1](os.environ[env])
        return os.environ[env]

    @property
    def group_rules(self):
        return self.__dict__["group_rules"]


settings = Settings()
