"""未签名本地来源的受控更新，与官方签名市场分离。"""

import asyncio
import hashlib
import io
import json
import re
import secrets
import shutil
import sqlite3
import stat
import time
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import uuid4

from packaging.version import Version
from sqlmodel import col, delete, select

from ab_sdk.events import PluginUpdateAvailable
from ab_sdk.manifest import check, load_manifest
from ab_sdk.updates import PluginUpdateInfo
from module.conf import settings
from module.models.plugin_kv import PluginKV
from module.plugin import host

from . import loader
from .downloads import database, digest
from .maintenance import BACKUP_ROOT, HostMaintenanceService, run_io

MAX_ZIP = 16 * 1024 * 1024
MAX_CONTENT = 64 * 1024 * 1024
_update_lock = asyncio.Lock()


async def fetch(url: str, limit: int) -> bytes:
    from module.network.request_url import get_shared_client

    client = await get_shared_client()
    async with client.stream(
        "GET", url, headers={"User-Agent": "AutoBangumi-Plugins"}
    ) as response:
        response.raise_for_status()
        if response.url.scheme != "https":
            raise ValueError("Update downloads require HTTPS")
        result = bytearray()
        async for chunk in response.aiter_bytes():
            result.extend(chunk)
            if len(result) > limit:
                raise ValueError("Plugin update exceeds size limit")
        return bytes(result)


def unpack(data: bytes, checksum: str, stage: Path, plugin_id: str, version: str):
    if hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError("Plugin checksum mismatch")
    stage.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > 2000 or sum(m.file_size for m in members) > MAX_CONTENT:
            raise ValueError("Plugin archive exceeds size limit")
        seen = set()
        for member in members:
            path = PurePosixPath(member.filename)
            normalized = str(path).casefold()
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in member.filename
                or PureWindowsPath(member.filename).drive
                or "\0" in member.filename
                or normalized in seen
                or stat.S_ISLNK(member.external_attr >> 16)
                or not path.parts
                or path.parts[0] in {".git", "__pycache__"}
            ):
                raise ValueError("Unsafe plugin archive path")
            seen.add(normalized)
            target = stage / path
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))
    manifest, errors = check(stage)
    if (
        errors
        or manifest is None
        or manifest.id != plugin_id
        or manifest.version != version
    ):
        raise ValueError("Plugin identity, version or SDK compatibility check failed")


class HostPluginUpdates:
    def __init__(self, plugin_id: str, data_dir: Path):
        self.plugin_id, self.data_dir = plugin_id, data_dir

    def _source(self):
        repository = settings.plugins.local_update_sources.get(self.plugin_id)
        root = loader.LOCAL_ROOT / self.plugin_id
        if (
            not settings.plugins.allow_unsigned
            or not repository
            or root.is_symlink()
            or not root.is_dir()
        ):
            raise ValueError(
                "Select an unsigned local plugin source in host settings first"
            )
        manifest = load_manifest(root)
        if manifest.id != self.plugin_id:
            raise ValueError("Installed plugin identity mismatch")
        return repository, root, manifest

    async def check(self):
        repository, _, current = self._source()
        release = json.loads(
            await fetch(
                f"https://api.github.com/repos/{repository}/releases/latest",
                1024 * 1024,
            )
        )
        tag = release.get("tag_name", "")
        version = tag.removeprefix("v")
        if (
            release.get("draft")
            or release.get("prerelease")
            or not re.fullmatch(r"\d+\.\d+\.\d+", version)
        ):
            raise ValueError("Local plugin updates require a stable version")
        name = f"{self.plugin_id}-{version}.zip"
        base = f"https://github.com/{repository}/releases/download/{tag}/"
        assets = {
            a["name"]: a["browser_download_url"] for a in release.get("assets", [])
        }
        if (
            assets.get(name) != base + name
            or assets.get(name + ".sha256") != base + name + ".sha256"
        ):
            raise ValueError("Update assets do not belong to the selected source")
        words = (await fetch(assets[name + ".sha256"], 4096)).decode().split()
        checksum = words[0].lower() if words else ""
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Invalid checksum file")
        token = secrets.token_urlsafe(24)
        info = PluginUpdateInfo(
            self.plugin_id,
            repository,
            current.version,
            version,
            Version(version) > Version(current.version),
            f"https://github.com/{repository}/releases/tag/{tag}",
            release.get("body", "")[:6000],
            token,
        )
        record = {
            "token": digest(token),
            "version": version,
            "current": current.version,
            "repository": repository,
            "sha256": checksum,
            "archive": assets[name],
            "expires": time.time() + 86400,
        }
        async with database() as db:
            await db.plugin_kv.set("core", f"local-update:{self.plugin_id}", record)
        if info.available:
            from module.notification import NotificationManager

            await NotificationManager().send_event(
                PluginUpdateAvailable(self.plugin_id, version, info.release_url)
            )
        return info

    async def install(self, version, *, install_token):
        from .maintenance import _application

        async with _update_lock:
            repository, root, current = self._source()
            async with database() as db:
                _, record = await db.plugin_kv.get(
                    "core", f"local-update:{self.plugin_id}"
                )
            if (
                not record
                or record["token"] != digest(install_token)
                or record["version"] != version
                or record["current"] != current.version
                or record["repository"] != repository
                or time.time() > record["expires"]
                or Version(version) <= Version(current.version)
            ):
                raise ValueError("Update preview expired; check again")
            if _application is None:
                raise RuntimeError("Update requires a running application")
            # 网络与包校验在停任务之前完成，固定 token 绑定来源、旧版本和校验和。
            data = await fetch(record["archive"], MAX_ZIP)
            work = loader.LOCAL_ROOT.parent / ".updates" / self.plugin_id / str(uuid4())
            stage, previous = work / "stage", work / "previous"
            try:
                await run_io(
                    unpack, data, record["sha256"], stage, self.plugin_id, version
                )

                async def update(progress):
                    selected_repo, _, selected_manifest = self._source()
                    if (
                        selected_repo != repository
                        or selected_manifest.version != current.version
                    ):
                        raise ValueError("Local update source or version changed")
                    backup = BACKUP_ROOT / self.plugin_id / progress.row.id
                    await run_io(shutil.copytree, root, backup / "code", symlinks=True)
                    details = {
                        "root": str(root),
                        "previous": str(previous),
                        "stage": str(stage),
                        "version": version,
                    }
                    await progress.checkpoint("replacing-code", details)

                    async def install_code():
                        root.rename(previous)
                        stage.rename(root)

                    async def rollback():
                        await self._restore(backup, root)

                    await _application.plugins.replace_local(
                        self.plugin_id, install_code, rollback
                    )
                    await progress.checkpoint("loaded", details)
                    async with database() as db:
                        await db.plugin_kv.delete(
                            "core", f"local-update:{self.plugin_id}"
                        )

                await HostMaintenanceService(self.plugin_id, self.data_dir).run(
                    "local-plugin-update", update
                )
            finally:
                # 旧代码与维护备份保留；未安装的 stage 可清理。崩溃记录可由 recover 恢复。
                if stage.exists():
                    await run_io(shutil.rmtree, stage)

    async def cached(self):
        async with database() as db:
            _, record = await db.plugin_kv.get("core", f"local-update:{self.plugin_id}")
        if not record:
            return None
        repository, _, current = self._source()
        if record["repository"] != repository or record["current"] != current.version:
            return None
        return {
            "version": record["version"],
            "available": Version(record["version"]) > Version(current.version),
        }

    async def _restore(self, backup: Path, root: Path):
        def restore_files():
            if root.exists():
                shutil.rmtree(root)
            shutil.copytree(backup / "code", root, symlinks=True)
            if self.data_dir.exists():
                shutil.rmtree(self.data_dir)
            if (backup / "plugin-data").exists():
                shutil.copytree(backup / "plugin-data", self.data_dir, symlinks=True)
            with sqlite3.connect(backup / "ab.db") as source:
                return source.execute(
                    "SELECT key, value FROM plugin_kv WHERE plugin_id = ?",
                    (self.plugin_id,),
                ).fetchall()

        values = await run_io(restore_files)
        async with database() as db:
            await db.begin_write()
            await db.session.execute(
                delete(PluginKV).where(col(PluginKV.plugin_id) == self.plugin_id)
            )
            for key, value in values:
                db.add(PluginKV(plugin_id=self.plugin_id, key=key, value=value))
            await db.commit()

    async def recover(self, operation_id):
        from module.models.plugin_maintenance import PluginMaintenanceRecord

        from .admission import _submit_lock
        from .library import organization_lock
        from .maintenance import _application, _lock

        if _application is None:
            raise RuntimeError("Update requires a running application")
        service = HostMaintenanceService(self.plugin_id, self.data_dir)
        status = await service.status(operation_id)
        if status.name != "local-plugin-update" or status.state not in {
            "running",
            "failed",
        }:
            raise ValueError("No interrupted update to recover")
        async with _update_lock, _lock, _application._lifecycle_lock:
            await _application.scheduler.stop_all()
            root = loader.LOCAL_ROOT / self.plugin_id
            if root.is_symlink():
                raise ValueError("Cannot restore a symlinked plugin directory")
            backup = BACKUP_ROOT / self.plugin_id / operation_id
            if not (backup / "code" / "plugin.toml").is_file():
                raise ValueError(
                    "Code backup unavailable; inspect the maintenance backup"
                )
            if load_manifest(backup / "code").id != self.plugin_id:
                raise ValueError("Backup plugin identity mismatch")
            async with _submit_lock, organization_lock:
                bus = host.get_bus()
                if bus is not None:
                    await bus.drain()
                await _application.plugins.restore_local(
                    self.plugin_id, lambda: self._restore(backup, root)
                )
            async with database() as db:
                row = await db.session.get(PluginMaintenanceRecord, operation_id)
                row.state, row.step = "acknowledged", "old-code-restored"
                db.add(row)
                await db.commit()


async def check_local_updates():
    for plugin_id in settings.plugins.local_update_sources:
        try:
            await HostPluginUpdates(
                plugin_id, Path("config/plugin-data") / plugin_id
            ).check()
        except Exception:
            # 不记录可能含代理凭据的异常正文。
            import logging

            logging.getLogger(__name__).warning(
                "Local plugin update check failed: %s", plugin_id
            )
