"""插件清单 ``plugin.toml`` 的解析与校验。"""

import re
import tomllib
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, Field, field_validator

from ab_sdk import SDK_VERSION

MANIFEST_NAME = "plugin.toml"
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ENTRY_RE = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")


class ManifestError(ValueError):
    pass


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str
    sdk: str = Field(description="依赖的 ab_sdk 版本范围，如 '>=0.1,<1'")
    entry: str = Field(description="'包.模块:Plugin子类'，相对插件根目录")
    description: str = ""
    authors: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not _ID_RE.match(value):
            raise ValueError("id 只能由小写字母、数字和连字符组成")
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
