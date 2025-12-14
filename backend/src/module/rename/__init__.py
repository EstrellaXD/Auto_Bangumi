from __future__ import annotations
from .renamer import Renamer, get_rename_config, set_rename_config
from .template_renderer import TemplateRenderer

from models.config import BangumiManage

__all__ = [
    "Renamer",
    "TemplateRenderer",
    "get_rename_config",
]


def init(config: BangumiManage | None = None):
    if config is None:
        from conf.config import get_config_by_key

        config = get_config_by_key("bangumi_manage", BangumiManage)
    set_rename_config(config)
