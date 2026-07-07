"""LLM 提供商插件安装管线（克隆 update.updater 的下载/验签/解包模式）。

安全边界与更新系统一致：
1. catalog.json 本身也验签（防索引篡改/降级）；
2. 每个插件 zip 校验 sha256 + ed25519 签名，拒绝未签名/坏签名；
3. _safe_extract 防 zip-slip；
4. manifest schema/id/entry/min_ab_version 逐项校验。
插件依赖仅限 stdlib + httpx + pydantic（应用已有），无 pip 安装。
"""

import asyncio
import hashlib
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import semver

from module.database import Database
from module.update.signing import DEFAULT_PUBKEY_PATH, verify_bundle_signature

logger = logging.getLogger(__name__)

# 插件目录与 catalog 托管位置。
GITHUB_OWNER = "EstrellaXD"
GITHUB_REPO = "Auto_Bangumi"
_CATALOG_TAG = "llm-plugins"
_RELEASE_BASE = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{_CATALOG_TAG}"
)
_DL_HEADERS = {"User-Agent": "AutoBangumi-Plugins"}
DEFAULT_PLUGINS_ROOT = Path("config") / "plugins"

_MANIFEST_SCHEMA = 1


def _meets_min_version(app_version: str, min_ab: str) -> bool:
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


def _safe_extract(zip_path: Path, dest: Path) -> None:
    """解压 zip 到 dest，拒绝绝对路径/`..` 越界成员（防 zip-slip）。"""
    import zipfile

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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class PluginInstaller:
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
        catalog_bytes = await self._download_bytes(f"{_RELEASE_BASE}/catalog.json")
        sig = await self._download_text(f"{_RELEASE_BASE}/catalog.json.sig")
        tmp = self.root / ".catalog.json"
        self.root.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(catalog_bytes)
        try:
            if not verify_bundle_signature(tmp, sig, self.pubkey_path):
                raise ValueError("catalog signature verification failed")
        finally:
            tmp.unlink(missing_ok=True)
        catalog = json.loads(catalog_bytes)
        if not isinstance(catalog, dict) or catalog.get("schema") != _MANIFEST_SCHEMA:
            raise ValueError("Unsupported catalog schema")
        plugins = catalog.get("plugins", [])
        return plugins if isinstance(plugins, list) else []

    def _is_builtin(self, plugin_id: str) -> bool:
        from module.parser.analyser.providers.builtin import BUILTIN
        from module.parser.analyser.providers.presets import PRESET_ADAPTERS

        return plugin_id in BUILTIN or plugin_id in PRESET_ADAPTERS

    async def install(self, plugin_id: str) -> InstallResult:
        async with self._lock:
            try:
                return await self._install(plugin_id)
            except Exception as e:  # noqa: BLE001 - 统一转成失败结果
                logger.warning("Plugin install failed for %s: %s", plugin_id, e)
                return InstallResult(success=False, message=str(e))

    async def _install(self, plugin_id: str) -> InstallResult:
        if self._is_builtin(plugin_id):
            return InstallResult(
                success=False, message=f"{plugin_id} is a builtin provider"
            )
        catalog = await self.fetch_catalog()
        entry = next((p for p in catalog if p.get("id") == plugin_id), None)
        if entry is None:
            return InstallResult(
                success=False, message=f"Plugin not found in catalog: {plugin_id}"
            )
        version = entry.get("version", "")
        min_ab = entry.get("min_ab_version", "0.0.0")
        if not _meets_min_version(self.app_version, min_ab):
            return InstallResult(
                success=False,
                message=f"Plugin requires AutoBangumi >= {min_ab}",
            )

        asset = entry.get("asset") or f"{plugin_id}-{version}.zip"
        zip_bytes = await self._download_bytes(f"{_RELEASE_BASE}/{asset}")
        if _sha256_bytes(zip_bytes) != entry.get("sha256"):
            return InstallResult(
                success=False, message="Plugin sha256 checksum mismatch"
            )

        staging = self.root / ".staging" / plugin_id
        staging.parent.mkdir(parents=True, exist_ok=True)
        zip_path = self.root / ".staging" / f"{plugin_id}.zip"
        zip_path.write_bytes(zip_bytes)
        sig = await self._download_text(f"{_RELEASE_BASE}/{asset}.sig")
        if not verify_bundle_signature(zip_path, sig, self.pubkey_path):
            zip_path.unlink(missing_ok=True)
            return InstallResult(success=False, message="Plugin signature invalid")

        _safe_extract(zip_path, staging)
        zip_path.unlink(missing_ok=True)

        manifest = self._read_manifest(staging)
        problem = self._validate_manifest(manifest, plugin_id)
        if problem:
            shutil.rmtree(staging, ignore_errors=True)
            return InstallResult(success=False, message=problem)

        # promote：config/plugins/<id>/<version>/ + installed.json
        target = self.root / plugin_id / version
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(target))
        (self.root / plugin_id / "installed.json").write_text(
            json.dumps({"version": version}), encoding="utf-8"
        )

        self._reload_registry(plugin_id)
        return InstallResult(success=True, version=version)

    def _read_manifest(self, unpacked: Path) -> dict:
        data = json.loads((unpacked / "plugin.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("plugin.json is not an object")
        return data

    def _validate_manifest(self, manifest: dict, plugin_id: str) -> Optional[str]:
        if manifest.get("schema") != _MANIFEST_SCHEMA:
            return "Unsupported plugin manifest schema"
        if manifest.get("id") != plugin_id:
            return "Plugin id mismatch between catalog and manifest"
        entry = manifest.get("entry", "")
        if ":" not in entry:
            return "Invalid plugin entry"
        min_ab = manifest.get("min_ab_version", "0.0.0")
        if not _meets_min_version(self.app_version, min_ab):
            return f"Plugin requires AutoBangumi >= {min_ab}"
        return None

    def _reload_registry(self, plugin_id: str) -> None:
        from module.parser import title_parser
        from module.parser.analyser.providers.registry import registry

        # 让全局注册表从本安装器的插件根扫描（生产环境两者默认同为
        # config/plugins；测试用 tmp_path 时也据此对齐）。
        registry._plugins_root = self.root
        registry.invalidate(plugin_id)
        title_parser.reset_cache()

    async def uninstall(self, plugin_id: str) -> InstallResult:
        async with self._lock:
            if self._is_builtin(plugin_id):
                return InstallResult(
                    success=False, message=f"{plugin_id} is a builtin provider"
                )
            plugin_dir = self.root / plugin_id
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir, ignore_errors=True)
            async with Database() as db:
                await db.llm_credential.delete(plugin_id)
            self._reload_registry(plugin_id)
            return InstallResult(success=True)
