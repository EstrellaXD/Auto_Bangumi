"""签名目录来源的安装管线（设计文档第 2.4 节），LLM 插件与通用插件共用。

安全边界与更新系统一致：

1. ``catalog.json`` 本身也验签（防索引篡改 / 降级）；
2. 每个插件 zip 校验 sha256 + ed25519 签名，拒绝未签名 / 坏签名；
3. ``_safe_extract`` 防 zip-slip；
4. 清单逐项校验后才落到 ``<root>/<id>/<version>/``，并写入版本指针
   ``installed.json``。

插件依赖限于 stdlib 与宿主已有的包，不做 pip 安装。

``SignedCatalogInstaller`` 是下载 / 验签 / 解包 / 落盘的共用部分，子类决定发布
tag、清单格式与安装后的刷新：``PluginInstaller`` 安装通用插件（``plugins`` tag，
``plugin.toml`` 清单），LLM 提供商插件的安装器在 ``module.llm_plugins``。
"""

import asyncio
import hashlib
import json
import logging
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Optional

import httpx
import semver

from ab_sdk.manifest import ID_RE, MANIFEST_NAME, RESERVED_IDS, check
from module.plugin.loader import BUILTIN_ROOT, INSTALLED_FILE, installed_version
from module.update.signing import DEFAULT_PUBKEY_PATH, verify_bundle_signature

logger = logging.getLogger(__name__)

# 插件目录与 catalog 托管位置。
GITHUB_OWNER = "EstrellaXD"
GITHUB_REPO = "Auto_Bangumi"
_DL_HEADERS = {"User-Agent": "AutoBangumi-Plugins"}
DEFAULT_PLUGINS_ROOT = Path("config") / "plugins"
# 通用插件目录的公钥（与在线更新分开的一把密钥，私钥在 CI 的 PLUGIN_SIGNING_KEY）：
# 插件签名只代表“维护者审查过这份代码”，不能用来批准更新包。放在 module/ 里，
# 随在线更新包一起分发（更新包本身由更新密钥验签），旧镜像更新后也能验签目录
PLUGIN_PUBKEY_PATH = Path(__file__).with_name("ab_plugin_pubkey.pem")


def release_base(tag: str) -> str:
    return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{tag}"


def meets_min_version(app_version: str, min_ab: str) -> bool:
    """app_version 是否满足 min_ab。非 semver 的开发版（DEV_VERSION）放行。"""
    try:
        return semver.VersionInfo.parse(app_version).compare(min_ab) >= 0
    except ValueError:
        return True


@dataclass
class InstallResult:
    success: bool
    version: str = ""
    message: str = ""


def safe_extract(zip_path: Path, dest: Path) -> None:
    """解压 zip 到 dest，拒绝绝对路径/`..` 越界成员（防 zip-slip）。"""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not target.is_relative_to(dest_resolved):
                raise ValueError(f"Unsafe path in plugin: {member}")
        zf.extractall(dest)


class SignedCatalogInstaller:
    tag: ClassVar[str]
    catalog_schema: ClassVar[int]
    # 版本目录里的清单文件名，卸载时据此确认目录归本安装器所有
    manifest_name: ClassVar[str]

    def __init__(
        self,
        *,
        root: Optional[Path] = None,
        pubkey_path: Optional[Path] = None,
        client: Optional[httpx.AsyncClient] = None,
        app_version: str = "0.0.0",
    ) -> None:
        self.root = root if root is not None else DEFAULT_PLUGINS_ROOT
        self.pubkey_path = pubkey_path or DEFAULT_PUBKEY_PATH
        self._client = client
        self.app_version = app_version
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------ 子类实现

    def _reject_reason(self, plugin_id: str) -> Optional[str]:
        """该 id 不允许经安装器安装 / 卸载的原因（如与内置同名）。"""
        raise NotImplementedError

    def _validate_manifest(
        self, unpacked: Path, entry: dict[str, Any]
    ) -> Optional[str]:
        """解包目录里的清单是否与 catalog 条目一致且可用；返回问题描述，通过时
        为 None。"""
        raise NotImplementedError

    def _check_entry(self, entry: dict[str, Any]) -> Optional[str]:
        """下载前对 catalog 条目的检查，默认只看宿主版本要求。"""
        min_ab = entry.get("min_ab_version", "0.0.0")
        if not meets_min_version(self.app_version, min_ab):
            return f"Plugin requires AutoBangumi >= {min_ab}"
        return None

    def _reload(self, plugin_id: str) -> None:
        """安装 / 卸载后让宿主看到变化（刷新缓存等）；默认没有。"""

    # ------------------------------------------------------------ 下载

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        from module.network.request_url import get_shared_client

        return await get_shared_client()

    async def _download_bytes(self, url: str) -> bytes:
        client = await self._get_client()
        resp = await client.get(url, headers=_DL_HEADERS)
        resp.raise_for_status()
        return resp.content

    async def _download_text(self, url: str) -> str:
        client = await self._get_client()
        resp = await client.get(url, headers=_DL_HEADERS)
        resp.raise_for_status()
        return resp.text

    async def fetch_catalog(self) -> list[dict]:
        """拉取并验签 catalog.json，返回插件条目列表。"""
        base = release_base(self.tag)
        catalog_bytes = await self._download_bytes(f"{base}/catalog.json")
        sig = await self._download_text(f"{base}/catalog.json.sig")
        tmp = self.root / ".catalog.json"
        self.root.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(catalog_bytes)
        try:
            if not verify_bundle_signature(tmp, sig, self.pubkey_path):
                raise ValueError("catalog signature verification failed")
        finally:
            tmp.unlink(missing_ok=True)
        catalog = json.loads(catalog_bytes)
        if (
            not isinstance(catalog, dict)
            or catalog.get("schema") != self.catalog_schema
        ):
            raise ValueError("Unsupported catalog schema")
        plugins = catalog.get("plugins", [])
        return plugins if isinstance(plugins, list) else []

    # ------------------------------------------------------------ 安装

    async def install(
        self, plugin_id: str, expected_version: str | None = None
    ) -> InstallResult:
        """expected_version：用户确认过的版本；目录已换成别的版本时拒绝安装，
        避免装上用户没看过权限的版本。"""
        async with self._lock:
            try:
                return await self._install(plugin_id, expected_version)
            except Exception as e:  # noqa: BLE001 - 统一转成失败结果
                logger.warning("Plugin install failed for %s: %s", plugin_id, e)
                return InstallResult(success=False, message=str(e))

    async def _install(
        self, plugin_id: str, expected_version: str | None
    ) -> InstallResult:
        if reason := self._check_id(plugin_id):
            return InstallResult(success=False, message=reason)
        catalog = await self.fetch_catalog()
        entry = next((p for p in catalog if p.get("id") == plugin_id), None)
        if entry is None:
            return InstallResult(
                success=False, message=f"Plugin not found in catalog: {plugin_id}"
            )
        if problem := self._check_entry(entry):
            return InstallResult(success=False, message=problem)
        version = entry.get("version", "")
        if expected_version is not None and version != expected_version:
            return InstallResult(
                success=False,
                message=f"Catalog version changed to {version}, please review again",
            )

        base = release_base(self.tag)
        asset = entry.get("asset") or f"{plugin_id}-{version}.zip"
        zip_bytes = await self._download_bytes(f"{base}/{asset}")
        if hashlib.sha256(zip_bytes).hexdigest() != entry.get("sha256"):
            return InstallResult(
                success=False, message="Plugin sha256 checksum mismatch"
            )

        staging = self.root / ".staging" / plugin_id
        staging.parent.mkdir(parents=True, exist_ok=True)
        zip_path = self.root / ".staging" / f"{plugin_id}.zip"
        zip_path.write_bytes(zip_bytes)
        sig = await self._download_text(f"{base}/{asset}.sig")
        if not verify_bundle_signature(zip_path, sig, self.pubkey_path):
            zip_path.unlink(missing_ok=True)
            return InstallResult(success=False, message="Plugin signature invalid")

        safe_extract(zip_path, staging)
        zip_path.unlink(missing_ok=True)

        problem = self._validate_manifest(staging, entry)
        if problem:
            shutil.rmtree(staging, ignore_errors=True)
            return InstallResult(success=False, message=problem)

        # promote：<root>/<id>/<version>/ + installed.json
        target = self.root / plugin_id / version
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(target))
        (self.root / plugin_id / INSTALLED_FILE).write_text(
            json.dumps({"version": version}), encoding="utf-8"
        )

        self._reload(plugin_id)
        return InstallResult(success=True, version=version)

    async def uninstall(self, plugin_id: str) -> InstallResult:
        async with self._lock:
            if reason := self._check_id(plugin_id):
                return InstallResult(success=False, message=reason)
            if reason := self._uninstall_reject_reason(plugin_id):
                return InstallResult(success=False, message=reason)
            shutil.rmtree(self.root / plugin_id, ignore_errors=True)
            await self._after_uninstall(plugin_id)
            self._reload(plugin_id)
            return InstallResult(success=True)

    def _check_id(self, plugin_id: str) -> Optional[str]:
        """id 不合法或不允许经安装器安装 / 卸载的原因；可以时为 None。"""
        # 同时挡住 "local"（本地插件目录）与路径穿越：id 会拼进文件系统路径
        if not ID_RE.match(plugin_id) or plugin_id in RESERVED_IDS:
            return f"Invalid plugin id: {plugin_id}"
        return self._reject_reason(plugin_id)

    def _uninstall_reject_reason(self, plugin_id: str) -> Optional[str]:
        # 只删经本安装器装入的目录（installed.json 指向含本类清单的版本目录），
        # 绝不碰 config/plugins/ 下的其它内容：本地插件、另一类安装器装入的插件
        version = installed_version(self.root, plugin_id)
        if (
            not version
            or not (self.root / plugin_id / version / self.manifest_name).is_file()
        ):
            return f"Plugin not installed: {plugin_id}"
        return None

    async def _after_uninstall(self, plugin_id: str) -> None:
        """卸载后清理插件的其它数据（如凭据）；默认没有。"""


class PluginInstaller(SignedCatalogInstaller):
    """通用插件（``plugin.toml``）：从 ``plugins`` tag 安装到 ``config/plugins/<id>/``。

    ``catalog.json`` 条目：``id``、``name``、``version``、``kind``、
    ``extension_points``、``sdk``、``min_ab_version``、``asset``、``sha256``、
    ``description``。zip 的内容在 zip 根（``ab-plugin pack`` 的产物）。
    """

    tag = "plugins"
    catalog_schema = 2
    manifest_name = MANIFEST_NAME

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("pubkey_path", PLUGIN_PUBKEY_PATH)
        super().__init__(**kwargs)

    def _reject_reason(self, plugin_id: str) -> Optional[str]:
        if (BUILTIN_ROOT / plugin_id).is_dir():
            return f"{plugin_id} is a builtin plugin"
        return None

    def _validate_manifest(
        self, unpacked: Path, entry: dict[str, Any]
    ) -> Optional[str]:
        parsed, problems = check(unpacked)
        if parsed is None or problems:
            return "; ".join(problems)
        if parsed.id != entry.get("id"):
            return "Plugin id mismatch between catalog and manifest"
        if parsed.version != entry.get("version"):
            return "Plugin version mismatch between catalog and manifest"
        return None
