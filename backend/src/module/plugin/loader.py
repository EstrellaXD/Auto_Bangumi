"""插件发现与代码加载。

来源（优先级从高到低，同 id 只取最高优先级来源）：

- ``builtin``：``module/plugins/builtin/<id>/``，随镜像发布
- ``local``：``config/plugins/local/<id>/``，用户二次开发，未签名
- ``pip``：``autobangumi.plugins`` entry point，未签名

目录型插件以 ``ab_plugin_<id>`` 为包名加载，插件内部可以使用相对导入；
``vendor/`` 下的纯 Python 依赖追加到 ``sys.path`` 末尾（宿主依赖优先）。
签名目录来源（由 LLM 插件安装器泛化）在 P2 接入。
"""

import importlib
import importlib.metadata
import importlib.resources
import importlib.util
import logging
import sys
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ab_sdk import Plugin

from .manifest import (
    MANIFEST_NAME,
    ManifestError,
    PluginManifest,
    load_manifest,
    parse_manifest,
)

logger = logging.getLogger(__name__)

PluginSource = Literal["builtin", "local", "pip"]

BUILTIN_ROOT = Path(__file__).resolve().parent.parent / "plugins" / "builtin"
LOCAL_ROOT = Path("config") / "plugins" / "local"
ENTRY_POINT_GROUP = "autobangumi.plugins"
_NATIVE_SUFFIXES = (".so", ".pyd", ".dylib", ".dll")


class PluginLoadError(Exception):
    pass


@dataclass
class PluginCandidate:
    manifest: PluginManifest
    source: PluginSource
    load: Callable[[], type[Plugin[Any]]]
    unload: Callable[[], None] = lambda: None
    # 插件根目录（web/ 静态资源从这里读取）；pip 包不在文件系统上时为 None
    root: Path | None = None

    @property
    def signed(self) -> bool:
        return self.source == "builtin"


@dataclass(frozen=True)
class DiscoveryError:
    location: str
    error: str


def discover(
    *,
    builtin_root: Path = BUILTIN_ROOT,
    local_root: Path = LOCAL_ROOT,
    entry_point_group: str = ENTRY_POINT_GROUP,
) -> tuple[list[PluginCandidate], list[DiscoveryError]]:
    """扫描全部来源并解析清单。目录来源不执行插件代码；pip 来源为读取包内
    清单会导入其顶层包（只在用户安装了该包时发生）。"""
    found: dict[str, PluginCandidate] = {}
    errors: list[DiscoveryError] = []

    def add(candidate: PluginCandidate) -> None:
        pid = candidate.manifest.id
        if pid in found:
            logger.warning(
                "[Plugin] %s 同时存在于 %s 与 %s，使用 %s",
                pid,
                found[pid].source,
                candidate.source,
                found[pid].source,
            )
            return
        found[pid] = candidate

    for source, root in (("builtin", builtin_root), ("local", local_root)):
        for plugin_dir in _plugin_dirs(root):
            try:
                add(_directory_candidate(plugin_dir, source))  # type: ignore[arg-type]
            except ManifestError as e:
                errors.append(DiscoveryError(str(plugin_dir), str(e)))
    for ep in importlib.metadata.entry_points(group=entry_point_group):
        try:
            add(_entry_point_candidate(ep))
        except (ManifestError, PluginLoadError) as e:
            errors.append(DiscoveryError(f"entry point {ep.name}", str(e)))
    for error in errors:
        logger.warning("[Plugin] 跳过 %s：%s", error.location, error.error)
    return list(found.values()), errors


def _plugin_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if (p / MANIFEST_NAME).is_file())


# ---------------------------------------------------------------- directory


def _directory_candidate(plugin_dir: Path, source: PluginSource) -> PluginCandidate:
    manifest = load_manifest(plugin_dir)
    if plugin_dir.name != manifest.id:
        raise ManifestError(f"{plugin_dir}: 目录名须与清单 id 一致（{manifest.id}）")
    package = "ab_plugin_" + manifest.id.replace("-", "_")
    return PluginCandidate(
        manifest=manifest,
        source=source,
        load=lambda: _load_directory(plugin_dir, manifest, package),
        unload=lambda: _unload_package(package, plugin_dir),
        root=plugin_dir,
    )


def _load_directory(
    plugin_dir: Path, manifest: PluginManifest, package: str
) -> type[Plugin[Any]]:
    _reject_native_code(plugin_dir)
    # 每次加载都从磁盘重新导入，配置变更后的重载能拿到最新代码
    _unload_package(package, plugin_dir)
    _activate_vendor(plugin_dir, manifest.id)
    pkg = types.ModuleType(package)
    pkg.__path__ = [str(plugin_dir)]
    pkg.__package__ = package
    sys.modules[package] = pkg
    importlib.invalidate_caches()
    try:
        module = importlib.import_module(f"{package}.{manifest.entry_module}")
    except Exception as e:
        _unload_package(package, plugin_dir)
        raise PluginLoadError(f"导入 {manifest.entry_module} 失败：{e}") from e
    return _resolve_class(module, manifest)


def _reject_native_code(plugin_dir: Path) -> None:
    for path in plugin_dir.rglob("*"):
        if path.suffix in _NATIVE_SUFFIXES:
            raise PluginLoadError(
                f"插件包含原生扩展 {path.relative_to(plugin_dir)}，只允许纯 Python 代码"
            )


def _activate_vendor(plugin_dir: Path, plugin_id: str) -> None:
    vendor = plugin_dir / "vendor"
    if not vendor.is_dir() or str(vendor) in sys.path:
        return
    for entry in vendor.iterdir():
        name = entry.stem if entry.suffix == ".py" else entry.name
        if not name.isidentifier():
            continue
        if importlib.util.find_spec(name) is not None:
            logger.warning(
                "[Plugin:%s] vendor 中的 %s 与已安装的同名包冲突，将使用已安装版本",
                plugin_id,
                name,
            )
    sys.path.append(str(vendor))


def _unload_package(package: str, plugin_dir: Path) -> None:
    for name in [n for n in sys.modules if n == package or n.startswith(package + ".")]:
        del sys.modules[name]
    vendor = str(plugin_dir / "vendor")
    if vendor in sys.path:
        sys.path.remove(vendor)


# ---------------------------------------------------------------- entry point


def _entry_point_candidate(ep: importlib.metadata.EntryPoint) -> PluginCandidate:
    top_package = ep.module.split(".", 1)[0]
    try:
        package_files = importlib.resources.files(top_package)
        text = (package_files / MANIFEST_NAME).read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError) as e:
        raise PluginLoadError(f"{top_package} 包内缺少 {MANIFEST_NAME}") from e
    manifest = parse_manifest(text, f"{top_package}/{MANIFEST_NAME}")

    def load() -> type[Plugin[Any]]:
        try:
            obj = ep.load()
        except Exception as e:
            raise PluginLoadError(f"加载 entry point {ep.value} 失败：{e}") from e
        return _check_class(obj, manifest)

    return PluginCandidate(
        manifest=manifest,
        source="pip",
        load=load,
        # zip 等非文件系统安装没有可直接提供的 web/ 目录
        root=package_files if isinstance(package_files, Path) else None,
    )


# ---------------------------------------------------------------- helpers


def _resolve_class(
    module: types.ModuleType, manifest: PluginManifest
) -> type[Plugin[Any]]:
    obj = getattr(module, manifest.entry_class, None)
    if obj is None:
        raise PluginLoadError(f"{manifest.entry} 不存在")
    return _check_class(obj, manifest)


def _check_class(obj: object, manifest: PluginManifest) -> type[Plugin[Any]]:
    if not (isinstance(obj, type) and issubclass(obj, Plugin)):
        raise PluginLoadError(f"{manifest.entry} 不是 ab_sdk.Plugin 的子类")
    return obj
