"""插件清单 ``plugin.toml`` 的解析与校验。"""

import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import Literal

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, Field, field_validator, model_validator

from ab_sdk import SDK_VERSION

from .host import CORE

MANIFEST_NAME = "plugin.toml"
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ENTRY_RE = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")
# 合法的 custom element 名（小写、含连字符），统一以 ab-plugin- 开头避免与宿主冲突
_ELEMENT_RE = re.compile(r"^ab-plugin-[a-z0-9]+(?:-[a-z0-9]+)*$")

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
    default_enabled: bool = Field(
        True, description="未设置启用开关时是否默认启用；只对内置插件生效"
    )
    ui: list[PluginUi] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not _ID_RE.match(value):
            raise ValueError("id 只能由小写字母、数字和连字符组成")
        if value == CORE:
            # core 是宿主内置实现的登记身份，插件占用会与之共享 Provider 归属
            raise ValueError(f"id {CORE!r} 为宿主保留")
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
