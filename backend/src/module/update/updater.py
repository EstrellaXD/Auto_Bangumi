"""在线自动更新的核心逻辑：GitHub Release 检查 + bundle 下载/校验/落地。

设计要点（见 docs/plans 与 CLAUDE.md）：

- 仓库固定为本项目（``EstrellaXD/Auto_Bangumi``），只从项目 Release 下载，
  不接受任意 URL。
- ``check_update`` 查询 Release 列表，按 channel（stable / 含预发布的 beta）用
  semver 选出最新版本并与当前运行版本比较，结果缓存约 15 分钟。
- ``apply_update`` 下载 bundle → 校验 sha256 → 解包读取 manifest → 检查
  ``min_image_version`` 兼容性 → 原子地把 staging 提升为 current（旧 current
  移到 backup）→ 写入 applied.json。真正的“重启以生效”由 API 层触发（进程退出，
  交给 Docker 的 restart 策略重跑 entrypoint 的覆盖层逻辑）。
- ``rollback`` 把 backup 换回 current（无 backup 则清除覆盖层回退到镜像版本）。

覆盖层文件都放在持久卷 ``config/updates/`` 下，因此容器重建后仍然保留。
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

import httpx
import semver
from pydantic import BaseModel

from module.conf import IMAGE_VERSION, VERSION
from module.database.migrations import CURRENT_SCHEMA_VERSION
from module.network.request_url import get_shared_client
from module.update.signing import DEFAULT_PUBKEY_PATH, verify_bundle_signature

logger = logging.getLogger(__name__)

# 固定的项目仓库，禁止从任意来源下载（安全约束）。
GITHUB_OWNER = "EstrellaXD"
GITHUB_REPO = "Auto_Bangumi"
_API_BASE = "https://api.github.com"

# check_update 结果缓存时长（秒）。
_CACHE_TTL = 15 * 60

# 覆盖层持久化根目录（相对运行时 cwd=/app，即 /app/config/updates）。
DEFAULT_UPDATES_ROOT = Path("config") / "updates"

_DL_HEADERS = {"User-Agent": "AutoBangumi-Updater"}
_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "AutoBangumi-Updater",
}


# --------------------------------------------------------------------------- 模型


class UpdateCheckResult(BaseModel):
    """``GET /update/check`` 的返回体：远端最新版本 + 本地覆盖层状态。"""

    current: str
    latest: Optional[str] = None
    has_update: bool = False
    channel: str = "stable"
    notes: str = ""
    published_at: Optional[str] = None
    is_prerelease: bool = False
    bundle_url: Optional[str] = None
    sha256_url: Optional[str] = None
    signature_url: Optional[str] = None
    # 本地覆盖层状态
    applied_version: Optional[str] = None
    can_rollback: bool = False
    error: Optional[str] = None


class ApplyResult(BaseModel):
    """``apply_update`` / ``rollback`` 的结果。"""

    success: bool
    message: str = ""
    version: Optional[str] = None
    restart_required: bool = False


@dataclass
class Progress:
    """在线更新进度，供 SSE 推送给前端。"""

    phase: str = (
        "idle"  # idle|checking|downloading|verifying|unpacking|promoting|restarting|error|done
    )
    percent: int = 0
    message: str = ""
    version: Optional[str] = None
    restart_required: bool = False
    error: Optional[str] = None


# --------------------------------------------------------------------------- 纯函数辅助


def _parse_semver(value: str) -> Optional[semver.VersionInfo]:
    try:
        return semver.VersionInfo.parse(value.lstrip("v"))
    except (ValueError, TypeError):
        return None


def _is_newer(candidate: str, base: str) -> bool:
    """candidate 是否严格新于 base（任一无法解析则返回 False）。"""
    a = _parse_semver(candidate)
    b = _parse_semver(base)
    if a is None or b is None:
        return False
    return a > b


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _reset_dir(path: Path) -> None:
    """清空并重建目录（用于 staging 暂存区）。"""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _safe_extract(zip_path: Path, dest: Path) -> None:
    """解压 zip 到 dest，拒绝绝对路径/`..` 越界成员（防 zip-slip）。"""
    _reset_dir(dest)
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not target.is_relative_to(dest_resolved):
                raise ValueError(f"Unsafe path in bundle: {member}")
        zf.extractall(dest)


def _read_manifest(unpacked: Path) -> dict:
    manifest_path = unpacked / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("manifest.json is not an object")
    return data


# --------------------------------------------------------------------------- Updater


class Updater:
    """检查/应用/回滚在线更新。依赖（root、版本、http client）可注入以便测试。"""

    def __init__(
        self,
        *,
        root: Optional[Path] = None,
        current_version: Optional[str] = None,
        image_version: Optional[str] = None,
        data_db: Optional[Path] = None,
        app_root: Optional[Path] = None,
        dependency_syncer: Optional[Callable[[Path], None]] = None,
        client: Optional[httpx.AsyncClient] = None,
        owner: str = GITHUB_OWNER,
        repo: str = GITHUB_REPO,
        pubkey_path: Optional[Path] = None,
    ) -> None:
        self.root = root if root is not None else DEFAULT_UPDATES_ROOT
        self.data_db = data_db if data_db is not None else Path("data") / "data.db"
        self.app_root = app_root if app_root is not None else Path(".")
        self.pubkey_path = (
            pubkey_path if pubkey_path is not None else DEFAULT_PUBKEY_PATH
        )
        self._dependency_syncer = dependency_syncer
        self.current_version = (
            current_version if current_version is not None else VERSION
        )
        self.image_version = (
            image_version if image_version is not None else IMAGE_VERSION
        )
        self._client = client
        self.owner = owner
        self.repo = repo
        self._lock = asyncio.Lock()
        self._cache: Optional[tuple[float, str, UpdateCheckResult]] = None
        self.progress = Progress()

    # -------------------------------------------------------------- 进度

    def _set_progress(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self.progress, key, value)

    def progress_dict(self) -> dict:
        return asdict(self.progress)

    # -------------------------------------------------------------- HTTP

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return await get_shared_client()

    async def _fetch_releases(self) -> list[dict]:
        client = await self._get_client()
        url = f"{_API_BASE}/repos/{self.owner}/{self.repo}/releases?per_page=20"
        resp = await client.get(url, headers=_API_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    async def _download_text(self, url: str) -> str:
        client = await self._get_client()
        resp = await client.get(url, headers=_DL_HEADERS)
        resp.raise_for_status()
        return resp.text

    async def _download_file(self, url: str, dest: Path) -> None:
        client = await self._get_client()
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with client.stream("GET", url, headers=_DL_HEADERS) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0) or 0)
            done = 0
            with open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes(1 << 16):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        self._set_progress(
                            phase="downloading",
                            percent=min(100, int(done * 100 / total)),
                            message="downloading bundle",
                        )

    # -------------------------------------------------------------- 检查

    def _find_bundle(
        self, assets: list[dict]
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        bundle_url: Optional[str] = None
        sha_url: Optional[str] = None
        sig_url: Optional[str] = None
        for asset in assets:
            name = asset.get("name", "")
            url = asset.get("browser_download_url")
            if not name.startswith("update-bundle") or not url:
                continue
            if name.endswith(".zip.sha256"):
                sha_url = url
            elif name.endswith(".zip.sig"):
                sig_url = url
            elif name.endswith(".zip"):
                bundle_url = url
        return bundle_url, sha_url, sig_url

    def _pick_release(self, releases: list[dict], channel: str) -> Optional[dict]:
        candidates: list[tuple[semver.VersionInfo, dict]] = []
        for rel in releases:
            if rel.get("draft"):
                continue
            if channel == "stable" and rel.get("prerelease"):
                continue
            ver = _parse_semver(rel.get("tag_name") or "")
            if ver is None:
                continue
            candidates.append((ver, rel))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[-1][1]

    def _applied_version(self) -> Optional[str]:
        applied = self.root / "applied.json"
        try:
            data = json.loads(applied.read_text(encoding="utf-8"))
            return data.get("version")
        except (OSError, ValueError):
            return None

    def _local_state(self, result: UpdateCheckResult) -> UpdateCheckResult:
        result.applied_version = self._applied_version()
        result.can_rollback = (self.root / "backup").exists()
        return result

    async def check_update(
        self, channel: str = "stable", *, force: bool = False
    ) -> UpdateCheckResult:
        now = time.monotonic()
        if not force and self._cache is not None:
            ts, cached_channel, cached = self._cache
            if cached_channel == channel and now - ts < _CACHE_TTL:
                return self._local_state(cached.model_copy())

        try:
            releases = await self._fetch_releases()
        except Exception as exc:  # 网络错误优雅降级
            logger.warning("[Update] release check failed: %s", exc)
            return self._local_state(
                UpdateCheckResult(
                    current=self.current_version,
                    channel=channel,
                    error=str(exc),
                )
            )

        latest = self._pick_release(releases, channel)
        if latest is None:
            return self._local_state(
                UpdateCheckResult(
                    current=self.current_version,
                    channel=channel,
                    error="no matching release found",
                )
            )

        latest_tag = (latest.get("tag_name") or "").lstrip("v")
        bundle_url, sha_url, sig_url = self._find_bundle(latest.get("assets") or [])
        has_update = (
            _is_newer(latest_tag, self.current_version) and bundle_url is not None
        )
        result = UpdateCheckResult(
            current=self.current_version,
            latest=latest_tag,
            has_update=has_update,
            channel=channel,
            notes=latest.get("body") or "",
            published_at=latest.get("published_at"),
            is_prerelease=bool(latest.get("prerelease")),
            bundle_url=bundle_url,
            sha256_url=sha_url,
            signature_url=sig_url,
        )
        self._cache = (now, channel, result)
        return self._local_state(result.model_copy())

    # -------------------------------------------------------------- 应用

    def _image_supports(self, min_image_version: str) -> bool:
        current = _parse_semver(self.image_version)
        required = _parse_semver(min_image_version)
        if current is None or required is None:
            # 镜像版本无法解析（开发/本地构建）时，不允许应用覆盖层。
            return False
        return current >= required

    def _fail(self, message: str) -> ApplyResult:
        logger.warning("[Update] %s", message)
        self._set_progress(phase="error", error=message, message=message)
        return ApplyResult(success=False, message=message)

    def _promote(
        self,
        unpacked: Path,
        version: str,
        sha256: str,
        manifest: dict,
        db_snapshot: Optional[dict],
        schema_version_before: Optional[int],
        bundle_zip: Optional[Path] = None,
        signature_b64: Optional[str] = None,
    ) -> None:
        """把解包好的 staging 提升为 current，旧 current 移到 backup。"""
        current = self.root / "current"
        backup = self.root / "backup"
        if backup.exists():
            shutil.rmtree(backup)
        if current.exists():
            os.rename(current, backup)
        os.rename(unpacked, current)

        # 留存已验签的 zip + 签名：boot_overlay 每次启动都据此重新验签并
        # 从 zip 解包（信任边界在镜像侧，不信任 ab 可写的 current/ 树）。
        # 旧的 bundle 挪到 -backup 供回滚换回。
        if bundle_zip is not None and signature_b64 is not None:
            retained = self.root / "bundle.zip"
            retained_sig = self.root / "bundle.zip.sig"
            for src, dst in (
                (retained, self.root / "bundle-backup.zip"),
                (retained_sig, self.root / "bundle-backup.zip.sig"),
            ):
                if src.exists():
                    os.replace(src, dst)
            os.replace(bundle_zip, retained)
            retained_sig.write_text(signature_b64.strip(), encoding="utf-8")

        lockfile = current / "backend" / "uv.lock"
        lock_sha = _sha256_file(lockfile) if lockfile.exists() else None
        # schema_version_after 不能在这里记录：新版本的迁移要到下次启动才会
        # 执行，此刻读库得到的仍是旧值。回滚时直接读活库比较。
        applied = {
            "version": version,
            "applied_at": int(time.time()),
            "sha256": sha256,
            "lockfile_sha256": manifest.get("lockfile_sha256") or lock_sha,
            "schema_version_before": schema_version_before,
            "db_backup": db_snapshot,
        }
        (self.root / "applied.json").write_text(
            json.dumps(applied, indent=2), encoding="utf-8"
        )

    def _snapshot_database(self) -> tuple[Optional[dict], Optional[int]]:
        """Back up the runtime SQLite DB before applying an overlay update."""
        schema_version = _read_db_schema_version(self.data_db)
        if not self.data_db.exists():
            return None, schema_version

        backup_dir = self.root / "db-backup"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        dest = backup_dir / self.data_db.name

        # sqlite3 backup API 透过 WAL 读出一致的独立快照，不需要（也不能）
        # 搭配活库的 -wal/-shm 边车文件——那属于另一个数据库实例，配对恢复
        # 会导致 WAL 帧错乱。
        with sqlite3.connect(self.data_db) as src, sqlite3.connect(dest) as dst:
            src.backup(dst)

        return (
            {
                "path": str(dest.relative_to(self.root)),
                "created_at": int(time.time()),
            },
            schema_version,
        )

    def _prepare_dependencies(self, unpacked: Path) -> None:
        """Resolve overlay dependencies before promotion so boot stays simple."""
        if self._dependency_syncer is not None:
            self._dependency_syncer(unpacked)
            return

        backend_dir = unpacked / "backend"
        overlay_lock = backend_dir / "uv.lock"
        if not overlay_lock.exists():
            return
        baseline_lock = self.app_root / "uv.lock"
        overlay_sha = _sha256_file(overlay_lock)
        baseline_sha = _sha256_file(baseline_lock) if baseline_lock.exists() else None
        if baseline_sha == overlay_sha:
            logger.info(
                "[Update] Dependencies unchanged from image baseline; skip sync."
            )
            return

        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("uv not found on PATH; cannot sync update dependencies")

        env = dict(os.environ)
        env["UV_PROJECT_ENVIRONMENT"] = str((unpacked / ".venv").resolve())
        logger.info("[Update] Syncing overlay dependencies into staged venv.")
        subprocess.run(
            [uv, "sync", "--frozen", "--no-dev"],
            cwd=str(backend_dir),
            env=env,
            check=True,
        )

    def _restore_database_snapshot(self, applied: dict) -> Optional[int]:
        # 只认 applied.json 里显式记录的快照；不回退到磁盘上残留的
        # db-backup/ 目录，否则第二次回滚会误还原上一轮更新的陈旧快照。
        snapshot = applied.get("db_backup") or {}
        rel_path = snapshot.get("path") if isinstance(snapshot, dict) else None
        if not rel_path:
            return None
        backup_db = self.root / rel_path
        if not backup_db.exists():
            return None

        self.data_db.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.data_db.with_name(self.data_db.name + ".rollback_tmp")
        shutil.copy2(backup_db, tmp)
        os.replace(tmp, self.data_db)
        # 快照是 backup API 生成的独立文件；活库残留的 -wal/-shm 必须清掉。
        for suffix in ("-wal", "-shm"):
            sidecar = self.data_db.with_name(self.data_db.name + suffix)
            try:
                sidecar.unlink()
            except FileNotFoundError:
                pass
        shutil.rmtree(backup_db.parent, ignore_errors=True)
        return _read_db_schema_version(self.data_db)

    async def apply_update(self, channel: str = "stable") -> ApplyResult:
        if self._lock.locked():
            return ApplyResult(
                success=False, message="an update is already in progress"
            )
        async with self._lock:
            try:
                self._set_progress(
                    phase="checking",
                    percent=0,
                    message="checking release",
                    version=None,
                    restart_required=False,
                    error=None,
                )
                result = await self.check_update(channel, force=True)
                if result.error:
                    return self._fail(f"check failed: {result.error}")
                if (
                    not result.has_update
                    or not result.bundle_url
                    or not result.sha256_url
                    or not result.latest
                ):
                    return self._fail("no update available")
                if not result.signature_url:
                    return self._fail(
                        "release has no bundle signature (.zip.sig); "
                        "refusing unsigned update"
                    )

                version = result.latest
                self.root.mkdir(parents=True, exist_ok=True)
                staging = self.root / "staging"
                await asyncio.to_thread(_reset_dir, staging)

                expected_raw = await self._download_text(result.sha256_url)
                expected_hash = expected_raw.strip().split()[0].lower()
                signature_b64 = await self._download_text(result.signature_url)

                zip_path = staging / "bundle.zip"
                await self._download_file(result.bundle_url, zip_path)

                self._set_progress(
                    phase="verifying", percent=100, message="verifying checksum"
                )
                actual_hash = (await asyncio.to_thread(_sha256_file, zip_path)).lower()
                if actual_hash != expected_hash:
                    return self._fail("sha256 mismatch; aborting update")
                if not await asyncio.to_thread(
                    verify_bundle_signature, zip_path, signature_b64, self.pubkey_path
                ):
                    return self._fail(
                        "bundle signature verification failed; aborting update"
                    )

                self._set_progress(phase="unpacking", message="unpacking bundle")
                unpacked = staging / "unpacked"
                await asyncio.to_thread(_safe_extract, zip_path, unpacked)
                manifest = await asyncio.to_thread(_read_manifest, unpacked)

                min_iv = manifest.get("min_image_version")
                if min_iv and not self._image_supports(str(min_iv)):
                    return self._fail(
                        f"image version {self.image_version} is too old for this "
                        f"update (requires >= {min_iv}); please pull a newer image"
                    )

                await asyncio.to_thread(self._prepare_dependencies, unpacked)
                db_snapshot, schema_version_before = await asyncio.to_thread(
                    self._snapshot_database
                )
                self._set_progress(phase="promoting", message="promoting update")
                await asyncio.to_thread(
                    self._promote,
                    unpacked,
                    version,
                    actual_hash,
                    manifest,
                    db_snapshot,
                    schema_version_before,
                    zip_path,
                    signature_b64,
                )
                self._cache = None  # 版本已变，作废检查缓存

                self._set_progress(
                    phase="restarting",
                    percent=100,
                    message="update applied, restarting",
                    version=version,
                    restart_required=True,
                    error=None,
                )
                return ApplyResult(
                    success=True,
                    version=version,
                    restart_required=True,
                    message="update applied; restarting to take effect",
                )
            except Exception as exc:  # noqa: BLE001 - 任何失败都要优雅返回
                logger.exception("[Update] apply failed")
                return self._fail(f"apply failed: {exc}")

    # -------------------------------------------------------------- 回滚

    async def rollback(self) -> ApplyResult:
        async with self._lock:
            try:
                current = self.root / "current"
                backup = self.root / "backup"
                applied = self.root / "applied.json"
                applied_data: dict = {}
                try:
                    applied_data = json.loads(applied.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass

                live_schema = _read_db_schema_version(self.data_db)
                if live_schema is not None and live_schema > CURRENT_SCHEMA_VERSION:
                    return self._fail(
                        "database schema is newer than this rollback code "
                        f"understands ({live_schema} > {CURRENT_SCHEMA_VERSION}); "
                        "refusing rollback"
                    )

                if backup.exists():
                    # current <-> backup 互换，使回滚本身可再次撤销。
                    swap = self.root / "_swap_tmp"
                    if swap.exists():
                        shutil.rmtree(swap)
                    if current.exists():
                        os.rename(current, swap)
                    os.rename(backup, current)
                    if swap.exists():
                        os.rename(swap, backup)

                    # bundle.zip(.sig) 与 bundle-backup.zip(.sig) 同步互换，
                    # boot_overlay 验签的对象要跟 current 树保持一致。
                    for name in ("bundle.zip", "bundle.zip.sig"):
                        cur = self.root / name
                        bak = self.root / name.replace("bundle", "bundle-backup", 1)
                        tmp = self.root / (name + ".swap_tmp")
                        if cur.exists():
                            os.replace(cur, tmp)
                        if bak.exists():
                            os.replace(bak, cur)
                        if tmp.exists():
                            os.replace(tmp, bak)

                    try:
                        version = _read_manifest(current).get("version")
                    except (OSError, ValueError):
                        version = None
                    # 只有当 schema 自 apply 后确实前进过（旧代码读不了新库）
                    # 才还原快照；schema 没变时保留活库，避免丢掉更新之后
                    # 写入的全部数据。
                    snapshot_schema = applied_data.get("schema_version_before")
                    restored_schema = None
                    if (
                        live_schema is not None
                        and snapshot_schema is not None
                        and live_schema != snapshot_schema
                    ):
                        logger.warning(
                            "[Update] Schema advanced since update (%s -> %s); "
                            "restoring pre-update database snapshot. Data written "
                            "since the update will be lost.",
                            snapshot_schema,
                            live_schema,
                        )
                        restored_schema = self._restore_database_snapshot(applied_data)
                    else:
                        logger.info(
                            "[Update] Schema unchanged since update; "
                            "keeping live database."
                        )
                    applied.write_text(
                        json.dumps(
                            {
                                "version": version,
                                "applied_at": int(time.time()),
                                "rolled_back": True,
                                "schema_version_before": live_schema,
                                "schema_version_after": restored_schema,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    message = "rolled back to previous version; restarting"
                else:
                    # 无备份：删除覆盖层，回退到镜像自带版本。
                    if current.exists():
                        shutil.rmtree(current)
                    if applied.exists():
                        applied.unlink()
                    for name in (
                        "bundle.zip",
                        "bundle.zip.sig",
                        "bundle-backup.zip",
                        "bundle-backup.zip.sig",
                    ):
                        (self.root / name).unlink(missing_ok=True)
                    version = self.image_version
                    message = "reverted to image version; restarting"

                self._cache = None
                self._set_progress(
                    phase="restarting",
                    percent=100,
                    message=message,
                    version=version,
                    restart_required=True,
                    error=None,
                )
                return ApplyResult(
                    success=True,
                    version=version,
                    restart_required=True,
                    message=message,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("[Update] rollback failed")
                return self._fail(f"rollback failed: {exc}")


# 进程级单例：API 与 SSE 共享同一个实例，使 apply 期间设置的进度对 SSE 可见。
updater = Updater()


def get_update_progress() -> dict:
    """供 SSE 端点读取当前更新进度。"""
    return updater.progress_dict()


def _read_db_schema_version(db_path: Path) -> Optional[int]:
    if not db_path.exists():
        return None
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='schema_version'"
            ).fetchone()
            if row is None:
                return 0
            version = conn.execute(
                "SELECT version FROM schema_version WHERE id = 1"
            ).fetchone()
            return int(version[0]) if version else 0
    except sqlite3.Error as exc:
        logger.warning("[Update] failed to read DB schema version: %s", exc)
        return None
