"""插件清单的解析与校验在 ``ab_sdk.manifest``（``ab-plugin`` 命令行共用），这里再导出。"""

from ab_sdk.manifest import (
    MANIFEST_NAME,
    ManifestError,
    PluginManifest,
    PluginUi,
    UiSlot,
    load_manifest,
    native_files,
    owns_element,
    parse_manifest,
)

__all__ = [
    "MANIFEST_NAME",
    "ManifestError",
    "PluginManifest",
    "PluginUi",
    "UiSlot",
    "load_manifest",
    "native_files",
    "owns_element",
    "parse_manifest",
]
