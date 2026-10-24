import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from module.models.config import Config
from module.update.v4 import migrate_v3_config, migrate_v3_dict

from .const import ENV_TO_ATTR

logger = logging.getLogger(__name__)
CONFIG_ROOT = Path("config")

# 与 api/config.py 的掩码约定保持一致（此处不 import，避免 conf ← api 循环）
_MASK_SENTINEL = "********"
_SENSITIVE_KEYS = ("password", "api_key", "token", "secret")


def _scrub_corrupted_masks(config: dict, path: str = "") -> None:
    """把字面写入配置的掩码哨兵按空值清洗。

    3.2.3/3.2.4 的配置接口只掩码不恢复，期间保存过配置的用户把 ``********``
    字面写进了密码/密钥字段（代理/下载器认证因此失败）。原值已不可恢复，
    置空并告警，提示用户重新输入。
    """
    for k, v in config.items():
        key_path = f"{path}.{k}" if path else k
        if isinstance(v, dict):
            _scrub_corrupted_masks(v, key_path)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    _scrub_corrupted_masks(item, f"{key_path}[{i}]")
        elif v == _MASK_SENTINEL and any(s in k.lower() for s in _SENSITIVE_KEYS):
            config[k] = ""
            logger.warning(
                "Config field '%s' contained a literal mask sentinel "
                "(corrupted by a 3.2.3/3.2.4 save); cleared it — re-enter "
                "the secret if one is required.",
                key_path,
            )


try:
    from module.__version__ import VERSION
except ImportError:
    logger.info("Can't find version info, use DEV_VERSION instead")
    VERSION = "DEV_VERSION"

# 镜像构建期写入的基线版本（见 Dockerfile 的 `RUN echo ... > /app/IMAGE_VERSION`）。
# 覆盖层（在线自动更新）应用后，运行版本 VERSION 会变成覆盖层版本，而
# IMAGE_VERSION 始终保持镜像自带的基线版本——用于判断“镜像 vs 覆盖层”谁更新，
# 以及在线更新的 min_image_version 兼容性检查。仓库/开发环境无此文件时回退到 VERSION。
IMAGE_VERSION_PATH = Path("/app/IMAGE_VERSION")
try:
    IMAGE_VERSION = IMAGE_VERSION_PATH.read_text(encoding="utf-8").strip() or VERSION
except OSError:
    IMAGE_VERSION = VERSION

CONFIG_PATH = (
    CONFIG_ROOT / "config_dev.json"
    if VERSION == "DEV_VERSION"
    else CONFIG_ROOT / "config.json"
).resolve()


class Settings(Config):
    """Runtime configuration singleton.

    On construction, migrates a 3.3 ``CONFIG_PATH`` to 4.0 (see
    ``module.update.v4``), loads it and immediately re-saves it; otherwise
    bootstraps defaults from environment variables via ``init()``.

    Use ``settings`` module-level instance rather than instantiating directly.
    """

    def __init__(self):
        super().__init__()
        if CONFIG_PATH.exists():
            # 必须先于 load / save：否则 3.3 的下载器等字段会被当作未知字段丢弃
            migrate_v3_config(CONFIG_PATH)
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
        # 每次 reload/重启都会触发 load，INFO 级别会在日志里反复刷屏
        logger.debug("Config loaded")

    @staticmethod
    def _migrate_old_config(config: dict) -> dict:
        """清洗字面写入的掩码哨兵（3.3 → 4.0 的字段迁移见 ``module.update.v4``）。"""
        _scrub_corrupted_masks(config)

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
                    section = config_dict.setdefault(key, {})
                    if isinstance(attr, list):
                        for _attr in attr:
                            attr_name = _attr[0] if isinstance(_attr, tuple) else _attr
                            section[attr_name] = self.__val_from_env(env, _attr)
                    else:
                        attr_name = attr[0] if isinstance(attr, tuple) else attr
                        section[attr_name] = self.__val_from_env(env, attr)
        # ENV_TO_ATTR 按 3.3 的位置写入（AB_DOWNLOADER_* → downloader、
        # AB_METHOD → bangumi_manage），再由迁移器移到默认下载器实例与 slots
        migrate_v3_dict(config_dict)
        config_obj = Config.model_validate(config_dict)
        self.__dict__.update(config_obj.__dict__)
        logger.debug("Config loaded from env")

    @staticmethod
    def __val_from_env(env: str, attr: tuple | str):
        """Return the environment variable value, applying the converter when attr is a tuple."""
        if isinstance(attr, tuple):
            return attr[1](os.environ[env])
        return os.environ[env]


settings = Settings()
