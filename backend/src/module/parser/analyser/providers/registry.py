"""LLM 提供商注册表：内置适配器 + base_url 预设 + 已安装插件的统一入口。

- ``list_infos()`` 只读静态描述（内置/预设直接读 info；插件读 manifest，
  首次不触发插件 Python 导入）；
- ``resolve()`` 返回适配器类，插件在首次 resolve 时才 import（懒加载）；
- ``invalidate()`` 在安装/卸载/升级后丢弃插件缓存。
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .base import LLMProviderAdapter, ProviderInfo
from .builtin import BUILTIN
from .presets import PRESET_ADAPTERS

logger = logging.getLogger(__name__)


class ProviderRegistry:
    def __init__(self, plugins_root: Optional[Path] = None) -> None:
        # 延迟到实际使用时再解析默认值，避免 import 期触达文件系统
        self._plugins_root = plugins_root
        self._plugin_cache: dict[str, type[LLMProviderAdapter]] = {}

    @property
    def plugins_root(self) -> Path:
        if self._plugins_root is not None:
            return self._plugins_root
        return Path("config") / "plugins"

    def _installed_manifests(self) -> dict[str, tuple[Path, dict]]:
        """扫描已安装插件目录，返回 {id: (版本目录, manifest)}，不导入代码。"""
        result: dict[str, tuple[Path, dict]] = {}
        root = self.plugins_root
        if not root.exists():
            return result
        for plugin_dir in root.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            pointer = plugin_dir / "installed.json"
            if not pointer.exists():
                continue
            try:
                version = json.loads(pointer.read_text(encoding="utf-8"))["version"]
                version_dir = plugin_dir / version
                manifest = json.loads(
                    (version_dir / "plugin.json").read_text(encoding="utf-8")
                )
            except Exception as e:  # noqa: BLE001 - 单个坏插件不应拖垮列举
                logger.warning("Skipping broken plugin %s: %s", plugin_dir.name, e)
                continue
            result[manifest["id"]] = (version_dir, manifest)
        return result

    def list_infos(self) -> list[ProviderInfo]:
        """列出全部可用提供商的静态描述（内置 → 预设 → 已安装插件）。"""
        infos = [cls.info for cls in (*BUILTIN.values(), *PRESET_ADAPTERS.values())]
        for plugin_id, (_, manifest) in self._installed_manifests().items():
            infos.append(
                ProviderInfo(
                    id=plugin_id,
                    display_name=manifest.get("name", plugin_id),
                    auth_kind=manifest.get("auth_kind", "api_key"),
                    builtin=False,
                    needs_base_url=manifest.get("needs_base_url", False),
                    default_model=manifest.get("default_model", ""),
                    plugin_version=manifest.get("version"),
                )
            )
        return infos

    def resolve(self, provider_id: str) -> type[LLMProviderAdapter]:
        """按 id 解析适配器类；未知 id 抛 ValueError。"""
        adapter_cls = BUILTIN.get(provider_id) or PRESET_ADAPTERS.get(provider_id)
        if adapter_cls is not None:
            return adapter_cls
        if provider_id in self._plugin_cache:
            return self._plugin_cache[provider_id]
        installed = self._installed_manifests().get(provider_id)
        if installed is not None:
            from module.llm_plugins.loader import load_adapter_class

            version_dir, manifest = installed
            loaded = load_adapter_class(version_dir, manifest)
            self._plugin_cache[provider_id] = loaded
            return loaded
        raise ValueError(f"Unsupported LLM provider: {provider_id}")

    def invalidate(self, provider_id: str | None = None) -> None:
        """插件安装/卸载后失效缓存。"""
        if provider_id is None:
            self._plugin_cache.clear()
        else:
            self._plugin_cache.pop(provider_id, None)


registry = ProviderRegistry()
