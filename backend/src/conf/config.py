"""config 的主要思路:
setting 会读取所有的配置,不管是不是自已需要的
不变的配置会在 setting 里放,不变是指不会有很多类型的, downloader 就会有很多种,
不常用的由 插件 自已从 setting 里面读
没有时自已将 setting 里加入自已的默认值
"""

import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from models.config import T,Program


logger = logging.getLogger(__name__)

def get_config_by_key(key: str, config_type: type[T]) -> T:
    """
    三层优先级加载配置：
    1. config.json 中的值（最高优先级）
    2. 环境变量（中等优先级）
    3. 默认值（最低优先级）

    Args:
        key: 配置键名
        config_type: 配置类型（必须继承 BaseSettings）

    Returns:
        配置实例
    """
    raw_config = settings.get(key, {})

    # 先创建实例，BaseSettings 会自动读取环境变量
    # 优先级：环境变量 > 默认值
    c = config_type()

    # 用 config.json 中的值覆盖，实现最高优先级
    # 只覆盖 config.json 中实际存在的字段
    if raw_config:
        # 将当前配置（环境变量+默认值）和 config.json 合并
        # config.json 的值会覆盖环境变量和默认值
        merged_config = {**c.model_dump(), **raw_config}
        c = config_type.model_validate(merged_config)

    # 判断现在的配置和 raw_config 是否一致，不一致则更新 config 文件
    # 这样可以将环境变量的值、新增的默认字段等写入配置文件
    current_dump = c.model_dump()
    if current_dump != raw_config:
        settings[key] = current_dump
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        logger.info(f"Config key '{key}' updated with new values")

    return c


_program_config: Program | None = None


def get_program_config() -> Program:
    """获取程序配置，如果未初始化则返回默认配置"""
    if _program_config is None:
        return Program()
    return _program_config


def set_program_config(config: Program):
    """设置程序配置"""
    global _program_config
    _program_config = config


# 加载 .env 文件中的环境变量
load_dotenv()

config_name = "config.json"
CONFIG_ROOT = Path("config")
CONFIG_PATH = (CONFIG_ROOT / config_name).resolve()
# 检查 config 目录是否存在,不存在则创建
if not CONFIG_ROOT.exists():
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
# 检查 config 文件是否存在,不存在则创建一个空文件
if not CONFIG_PATH.exists():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write("{}")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        settings = json.load(f)
except json.JSONDecodeError:
    logger.error(f"Config file {CONFIG_PATH} is not a valid JSON file.")
    settings = {}

set_program_config(get_config_by_key("program", Program))



# class Settings(Config):
#     # def __init__(self):
#     #     super().__init__()
#     def __init__(self, **data):
#         super().__init__(**data)
#         if not data:
#             if CONFIG_PATH.exists():
#                 self.load()
#                 self.save()
#             else:
#                 self.init()
#
#     def load(self):
#         with open(CONFIG_PATH, "r", encoding="utf-8") as f:
#             config = json.load(f)
#         update_config(self, config)
#         logger.info("Config loaded")
#
#     def save(self, config_dict: dict | None = None):
#         if not config_dict:
#             config_dict = self.model_dump()
#         with open(CONFIG_PATH, "w", encoding="utf-8") as f:
#             json.dump(config_dict, f, indent=4, ensure_ascii=False)
#
#     def init(self):
#         load_dotenv(".env")
#         self.__load_from_env()
#         self.save()
#
#     def __load_from_env(self):
#         config_dict = self.model_dump()
#         for key, section in ENV_TO_ATTR.items():
#             for env, attr in section.items():
#                 if env in os.environ:
#                     if isinstance(attr, list):
#                         for _attr in attr:
#                             # TODO: 这里会永远是 True,之后看看删了 if
#                             attr_name = _attr[0] if isinstance(_attr, tuple) else _attr
#                             config_dict[key][attr_name] = self.__val_from_env(env, _attr)
#                     else:
#                         attr_name = attr[0] if isinstance(attr, tuple) else attr
#                         config_dict[key][attr_name] = self.__val_from_env(env, attr)
#         config_obj = Config.model_validate(config_dict)
#         self.__dict__.update(config_obj.__dict__)
#         logger.info("Config loaded from env")
#
#     @staticmethod
#     def __val_from_env(env: str, attr: tuple[str, Callable[..., Any]] | str):
#         if isinstance(attr, tuple):
#             conv_func = attr[1]
#             return conv_func(os.environ[env])
#         else:
#             return os.environ[env]
#
#
# settings = Settings()
