"""插件清单 ``plugin.toml`` 的解析与校验。

宿主加载器与 ``ab-plugin`` 命令行共用，所以放在 SDK 里：插件作者不装宿主也能校验。
"""

import os
import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import Literal

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, Field, field_validator, model_validator

from . import SDK_VERSION

MANIFEST_NAME = "plugin.toml"
# 只允许纯 Python 代码（设计文档第 2.4 节）：带这些后缀的文件一律拒绝
NATIVE_SUFFIXES = (".so", ".pyd", ".dylib", ".dll")
# 工具链产生的目录（虚拟环境、缓存、构建产物）：不属于插件代码，扫描与打包都跳过
TOOLING_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "dist",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }
)
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ENTRY_RE = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")
# 合法的 custom element 名（小写、含连字符），统一以 ab-plugin- 开头避免与宿主冲突
_ELEMENT_RE = re.compile(r"^ab-plugin-[a-z0-9]+(?:-[a-z0-9]+)*$")

# 不可被插件占用的 id：core 是宿主内置实现的登记身份，插件占用会与之共享
# Provider 归属；local 是 config/plugins/ 下本地插件的目录名，与签名目录
# 安装位置 config/plugins/<id>/ 冲突
CORE_PLUGIN_ID = "core"
RESERVED_IDS = frozenset({CORE_PLUGIN_ID, "local"})

# 前端挂载点（第 3.8 节）
UiSlot = Literal[
    "settings.section",
    "bangumi.detail.tab",
    "bangumi.card.action",
    "page",
    "dashboard.widget",
]


def owns_element(plugin_id: str, element: str) -> bool:
    """element 是否落在 ``ab-plugin-<id>`` 命名空间内。"""
    prefix = f"ab-plugin-{plugin_id}"
    return element == prefix or element.startswith(prefix + "-")


class ManifestError(ValueError):
    pass


class PluginUi(BaseModel):
    """``[[plugin.ui]]``：插件 ``web/`` 下的 ES module 定义的 custom element
    挂到宿主的哪个位置。"""

    slot: UiSlot
    element: str = Field(description="custom element 名，须以 ab-plugin- 开头")
    entry: str = Field(
        description="定义该元素的 ES module，相对插件根目录，位于 web/ 下"
    )
    title: dict[str, str] = Field(
        min_length=1, description="按语言的标题，如 {zh-CN = '…', en-US = '…'}"
    )

    @field_validator("element")
    @classmethod
    def _check_element(cls, value: str) -> str:
        if not _ELEMENT_RE.match(value):
            raise ValueError("element 须为以 ab-plugin- 开头的小写 custom element 名")
        return value

    @field_validator("entry")
    @classmethod
    def _check_entry(cls, value: str) -> str:
        parts = PurePosixPath(value).parts
        if "\\" in value or len(parts) < 2 or parts[0] != "web" or ".." in parts:
            raise ValueError("entry 须为 web/ 下的相对路径，如 'web/index.js'")
        return value


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str
    sdk: str = Field(description="依赖的 ab_sdk 版本范围，如 '>=0.1,<1'")
    entry: str = Field(description="'包.模块:Plugin子类'，相对插件根目录")
    description: str = ""
    authors: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    extension_points: list[str] = Field(
        default_factory=list,
        description="提供的扩展点（仅供签名目录展示，宿主以实际登记为准）",
    )
    default_enabled: bool = Field(
        True, description="未设置启用开关时是否默认启用；只对内置插件生效"
    )
    ui: list[PluginUi] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not ID_RE.match(value):
            raise ValueError("id 只能由小写字母、数字和连字符组成")
        if value in RESERVED_IDS:
            raise ValueError(f"id {value!r} 为宿主保留")
        return value

    @field_validator("version")
    @classmethod
    def _check_version(cls, value: str) -> str:
        try:
            Version(value)
        except InvalidVersion as e:
            raise ValueError(f"无效版本号：{value}") from e
        return value

    @field_validator("sdk")
    @classmethod
    def _check_sdk(cls, value: str) -> str:
        try:
            SpecifierSet(value)
        except InvalidSpecifier as e:
            raise ValueError(f"无效的 sdk 版本范围：{value}") from e
        return value

    @field_validator("entry")
    @classmethod
    def _check_entry(cls, value: str) -> str:
        if not _ENTRY_RE.match(value):
            raise ValueError("entry 须形如 'my_plugin:MyPlugin'")
        return value

    @model_validator(mode="after")
    def _check_ui_elements(self) -> "PluginManifest":
        # custom element 名是全局的：限定在 ab-plugin-<id> 命名空间内，
        # 一个插件才不会占用别的插件的元素名
        for ui in self.ui:
            if not owns_element(self.id, ui.element):
                raise ValueError(
                    f"element {ui.element!r} 须为 ab-plugin-{self.id} "
                    f"或以 ab-plugin-{self.id}- 开头"
                )
        return self

    @property
    def entry_module(self) -> str:
        return self.entry.split(":", 1)[0]

    @property
    def entry_class(self) -> str:
        return self.entry.split(":", 1)[1]

    def sdk_compatible(self, sdk_version: str = SDK_VERSION) -> bool:
        # 0.x 期间允许预发布版本匹配，便于用 beta SDK 开发
        return SpecifierSet(self.sdk).contains(sdk_version, prereleases=True)


def parse_manifest(text: str, source: str = MANIFEST_NAME) -> PluginManifest:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ManifestError(f"{source}: TOML 语法错误：{e}") from e
    table = data.get("plugin")
    if not isinstance(table, dict):
        raise ManifestError(f"{source}: 缺少 [plugin] 表")
    try:
        return PluginManifest.model_validate(table)
    except ValueError as e:
        raise ManifestError(f"{source}: {e}") from e


def load_manifest(plugin_dir: Path) -> PluginManifest:
    path = plugin_dir / MANIFEST_NAME
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ManifestError(f"{path}: 无法读取：{e}") from e
    return parse_manifest(text, str(path))


def native_files(plugin_dir: Path) -> list[Path]:
    """插件目录中的原生扩展文件（相对路径）。"""
    found = []
    for root, dirs, names in os.walk(plugin_dir):
        dirs[:] = sorted(d for d in dirs if d not in TOOLING_DIRS)
        found += [
            (Path(root) / n).relative_to(plugin_dir)
            for n in names
            if n.endswith(NATIVE_SUFFIXES)
        ]
    return sorted(found)


def check(plugin_dir: Path) -> tuple[PluginManifest | None, list[str]]:
    """校验插件目录：清单、SDK 版本范围、入口与前端文件、原生扩展。"""
    try:
        manifest = load_manifest(plugin_dir)
    except ManifestError as e:
        return None, [str(e)]
    problems = []
    if not manifest.sdk_compatible():
        problems.append(f"需要 ab_sdk {manifest.sdk}，当前 SDK 为 {SDK_VERSION}")
    module = Path(*manifest.entry_module.split("."))
    if not any(
        (plugin_dir / candidate).is_file()
        for candidate in (module.with_suffix(".py"), module / "__init__.py")
    ):
        problems.append(f"入口模块 {manifest.entry_module} 不存在")
    for ui in manifest.ui:
        if not (plugin_dir / ui.entry).is_file():
            problems.append(f"前端入口 {ui.entry} 不存在")
    problems += [
        f"含原生扩展 {p}，只允许纯 Python 代码" for p in native_files(plugin_dir)
    ]
    return manifest, problems
