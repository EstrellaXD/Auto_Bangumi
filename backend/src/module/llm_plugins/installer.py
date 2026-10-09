"""LLM 提供商插件安装管线（下载 / 验签 / 解包由 ``module.plugin.installer`` 提供）。

LLM 插件仍使用 ``plugin.json`` 清单，发布在 ``llm-plugins`` tag；通用插件走
``module.plugin.installer.PluginInstaller``。
"""

import json
from pathlib import Path
from typing import Any, Optional

from module.database import Database
from module.plugin.installer import (
    DEFAULT_PLUGINS_ROOT,
    InstallResult,
    SignedCatalogInstaller,
    meets_min_version,
)

__all__ = ["DEFAULT_PLUGINS_ROOT", "InstallResult", "PluginInstaller"]

_MANIFEST_SCHEMA = 1


class PluginInstaller(SignedCatalogInstaller):
    tag = "llm-plugins"
    catalog_schema = _MANIFEST_SCHEMA
    manifest_name = "plugin.json"

    def _reject_reason(self, plugin_id: str) -> Optional[str]:
        from module.parser.analyser.providers.builtin import BUILTIN
        from module.parser.analyser.providers.presets import PRESET_ADAPTERS

        if plugin_id in BUILTIN or plugin_id in PRESET_ADAPTERS:
            return f"{plugin_id} is a builtin provider"
        return None

    def _validate_manifest(
        self, unpacked: Path, entry: dict[str, Any]
    ) -> Optional[str]:
        manifest = json.loads((unpacked / "plugin.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("plugin.json is not an object")
        if manifest.get("schema") != _MANIFEST_SCHEMA:
            return "Unsupported plugin manifest schema"
        if manifest.get("id") != entry.get("id"):
            return "Plugin id mismatch between catalog and manifest"
        if ":" not in manifest.get("entry", ""):
            return "Invalid plugin entry"
        min_ab = manifest.get("min_ab_version", "0.0.0")
        if not meets_min_version(self.app_version, min_ab):
            return f"Plugin requires AutoBangumi >= {min_ab}"
        return None

    def _reload(self, plugin_id: str) -> None:
        from module.parser import title_parser
        from module.parser.analyser.providers.registry import registry

        # 让全局注册表从本安装器的插件根扫描（生产环境两者默认同为
        # config/plugins；测试用 tmp_path 时也据此对齐）。
        registry._plugins_root = self.root
        registry.invalidate(plugin_id)
        title_parser.reset_cache()

    async def _after_uninstall(self, plugin_id: str) -> None:
        async with Database() as db:
            await db.llm_credential.delete(plugin_id)
