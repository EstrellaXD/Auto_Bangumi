"""从已安装的插件树按 manifest.entry 加载适配器类。

用版本化的模块名（``ab_llm_plugin_{id}_{ver}``）+ spec_from_file_location
加载，不污染 sys.path，升级时新版本是全新模块名 → 热加载无需重启。
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _module_name(plugin_id: str, version: str) -> str:
    safe = plugin_id.replace("-", "_")
    return f"ab_llm_plugin_{safe}_{version.replace('.', '_')}"


def load_adapter_class(plugin_dir: Path, manifest: dict) -> type:
    """加载并返回 manifest.entry 指定的适配器类。

    entry 形如 ``pkg.module:ClassName``。校验类继承 LLMProviderAdapter 且
    info.id 与 manifest id 一致（防止 zip 内混入冒名适配器）。
    """
    from module.parser.analyser.providers.base import LLMProviderAdapter

    entry = manifest.get("entry", "")
    if ":" not in entry:
        raise ValueError(f"Invalid plugin entry: {entry!r}")
    module_path, class_name = entry.split(":", 1)
    rel = module_path.replace(".", "/") + ".py"
    file_path = plugin_dir / rel
    if not file_path.exists():
        raise ValueError(f"Plugin entry module not found: {rel}")

    mod_name = _module_name(manifest["id"], manifest["version"])
    spec = importlib.util.spec_from_file_location(
        mod_name,
        file_path,
        submodule_search_locations=[str(plugin_dir)],
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load plugin module: {mod_name}")
    module: Any = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(mod_name, None)
        raise

    adapter_cls = getattr(module, class_name, None)
    if adapter_cls is None:
        raise ValueError(f"Plugin class not found: {class_name}")
    if not (
        isinstance(adapter_cls, type) and issubclass(adapter_cls, LLMProviderAdapter)
    ):
        raise ValueError(f"{class_name} is not an LLMProviderAdapter")
    if adapter_cls.info.id != manifest["id"]:
        raise ValueError(
            f"Adapter id {adapter_cls.info.id!r} != manifest id {manifest['id']!r}"
        )
    return adapter_cls
