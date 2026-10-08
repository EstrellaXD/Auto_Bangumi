"""3.3 → 4.0 配置迁移（设计文档第 9 节）。

只迁移 4.0 中已有去处的字段：

- ``downloader`` → ``plugins.instances`` 中 id 为 ``default`` 的下载器实例，
  ``plugins.slots.downloader = "default"``
- ``bangumi_manage.rename_method`` → ``plugins.slots.rename_strategy``
  （废弃的 ``normal`` 改为 ``none``）
- ``bangumi_manage.revision_conflict_policy`` → ``plugins.slots.conflict_policy``
- 通知渠道的旧字段别名：Bark 的 ``token`` → ``device_key``，WeCom 的 ``chat_id``
  → ``webhook_url``（渠道实现不再读旧字段）

在 ``Settings`` 读写配置文件之前运行。改写前把原文件备份为 ``<文件名>.v3.bak``；
失败时从备份恢复并抛出 :class:`ConfigMigrationError`，拒绝启动。
本模块不能 import ``module.conf``：它在 ``settings`` 构造之前被调用。
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from module.models.config import DEFAULT_DOWNLOADER_ID, DOWNLOADER_POINT, Config

logger = logging.getLogger(__name__)

_SLOT_FIELDS = {
    "rename_method": "rename_strategy",
    "revision_conflict_policy": "conflict_policy",
}


# 渠道类型 → (旧字段, 新字段)；3.x 的渠道实现以 ``新字段 or 旧字段`` 读取
_PROVIDER_ALIASES = {
    "bark": ("token", "device_key"),
    "wecom": ("chat_id", "webhook_url"),
}


class ConfigMigrationError(RuntimeError):
    """配置迁移失败；配置文件已从备份恢复。"""


def _section(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigMigrationError(f"config migration failed at {key}: not an object")
    return value


def migrate_v3_dict(config: dict[str, Any]) -> list[str]:
    """就地把 3.3 的字段移到 4.0 的位置，返回被移动的字段（空列表表示无需迁移）。

    下载器字段合并到已有的 ``default`` 实例上，没有时新建；未出现的字段保持原样。
    """
    return _migrate_plugin_fields(config) + _migrate_provider_aliases(config)


def _migrate_provider_aliases(config: dict[str, Any]) -> list[str]:
    moved = []
    providers = _section(config, "notification").get("providers")
    for i, provider in enumerate(providers if isinstance(providers, list) else []):
        if not isinstance(provider, dict):
            continue
        old, new = _PROVIDER_ALIASES.get(
            str(provider.get("type", "")).lower(), ("", "")
        )
        if old in provider:
            legacy = provider.pop(old)
            provider[new] = provider.get(new) or legacy
            moved.append(f"notification.providers[{i}].{old}")
    return moved


def _migrate_plugin_fields(config: dict[str, Any]) -> list[str]:
    downloader = _section(config, "downloader")
    bangumi_manage = _section(config, "bangumi_manage")
    moved = [f"bangumi_manage.{key}" for key in _SLOT_FIELDS if key in bangumi_manage]
    if "downloader" in config:
        moved.insert(0, "downloader")
    if not moved:
        return moved

    plugins = config.setdefault("plugins", {})
    slots = plugins.setdefault("slots", {})
    if "downloader" in config:
        config.pop("downloader")
        options = dict(downloader)
        instances = plugins.setdefault("instances", [])
        instance = next(
            (i for i in instances if i.get("id") == DEFAULT_DOWNLOADER_ID), None
        )
        if instance is None:
            instance = {
                "id": DEFAULT_DOWNLOADER_ID,
                "point": DOWNLOADER_POINT,
                "provider": "qbittorrent",
                "options": {},
            }
            instances.append(instance)
        instance["provider"] = options.pop("type", instance["provider"])
        instance["options"].update(options)
        slots["downloader"] = DEFAULT_DOWNLOADER_ID
    for old, slot in _SLOT_FIELDS.items():
        if old in bangumi_manage:
            slots[slot] = bangumi_manage.pop(old)
    if slots.get("rename_strategy") == "normal":
        slots["rename_strategy"] = "none"
    return moved


def _failed_field(error: Exception) -> str:
    if isinstance(error, ValidationError):
        first = error.errors(include_url=False)[0]
        loc = ".".join(str(p) for p in first["loc"])
        return f"{loc}: {first['msg']}"
    return str(error)


def migrate_v3_config(path: Path) -> bool:
    """迁移 ``path`` 处的配置文件，返回是否改写了文件。已是 4.0 格式时什么也不做。"""
    config = json.loads(path.read_text(encoding="utf-8"))
    moved = migrate_v3_dict(config)
    if not moved:
        return False
    # 已有的备份不覆盖（降级回 3.3 再升级时，第一份备份里才有真实的下载器
    # 凭据），本次备份另取 .v3.bak.1、.v3.bak.2 …
    backup = path.with_name(path.name + ".v3.bak")
    n = 0
    while backup.exists():
        n += 1
        backup = path.with_name(f"{path.name}.v3.bak.{n}")
    shutil.copy2(path, backup)
    try:
        Config.model_validate(config)
        # 先写临时文件再替换：中途崩溃不会留下半个配置文件
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(tmp, path)
    except Exception as e:
        shutil.copy2(backup, path)
        message = (
            f"config migration to 4.0 failed at {_failed_field(e)}; "
            f"{path.name} was restored from {backup.name}. Fix the field and restart. "
            f"配置迁移失败，已从备份恢复 {path.name}，请修正该字段后重新启动。"
        )
        logger.critical(message)
        raise ConfigMigrationError(message) from e
    logger.info(
        "Migrated %s to 4.0 (%s); the 3.3 file is kept as %s",
        path.name,
        ", ".join(moved),
        backup.name,
    )
    return True
