"""在线自动更新测试：check / apply / rollback、boot_overlay 覆盖层、以及三个
端点的 path+verb+鉴权契约。

网络与文件系统全部 mock：GitHub Release API 与下载走 httpx.MockTransport，
覆盖层落地走 tmp_path，进程退出被打桩以确保测试不会真的退出。
"""

import asyncio
import base64
import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.security.api import get_current_user
from module.update.updater import Updater, _is_newer, _parse_semver

# 测试用签名密钥对：私钥签 bundle，公钥写到 tmp 供 Updater 验签。
_TEST_SIGNING_KEY = Ed25519PrivateKey.generate()


def _sign_bytes(data: bytes) -> str:
    return base64.b64encode(_TEST_SIGNING_KEY.sign(data)).decode()


def _write_test_pubkey(dest_dir: Path) -> Path:
    pem = _TEST_SIGNING_KEY.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path = dest_dir / "ab_update_pubkey.pem"
    path.write_bytes(pem)
    return path


# ---------------------------------------------------------------------------
# Helpers: build a fake release + a real bundle zip served by a MockTransport
# ---------------------------------------------------------------------------


def _make_bundle(version: str, min_image_version: str = "3.3.0-beta.1") -> bytes:
    """构造一个合法的 update bundle zip（内存字节）。"""
    lock_content = f"# uv.lock for {version}\n".encode()
    lock_sha = hashlib.sha256(lock_content).hexdigest()
    manifest = {
        "version": version,
        "min_image_version": min_image_version,
        "lockfile_sha256": lock_sha,
        "notes": "test notes",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("backend/src/module/__marker__.txt", f"module {version}")
        zf.writestr("backend/pyproject.toml", "[project]\nname='x'\n")
        zf.writestr("backend/uv.lock", lock_content)
        zf.writestr("webui-dist/index.html", f"<html>{version}</html>")
        zf.writestr("manifest.json", json.dumps(manifest))
    return buf.getvalue()


def _releases_payload(bundle_bytes: bytes, sha_text: str) -> list[dict]:
    """模拟 GitHub /releases 列表：一个 stable 与一个更高的 beta 预发布。"""
    stable_assets = [
        {
            "name": "update-bundle-3.2.0.zip",
            "browser_download_url": "https://dl.test/stable/bundle.zip",
        },
        {
            "name": "update-bundle-3.2.0.zip.sha256",
            "browser_download_url": "https://dl.test/stable/bundle.sha256",
        },
        {
            "name": "update-bundle-3.2.0.zip.sig",
            "browser_download_url": "https://dl.test/stable/bundle.sig",
        },
    ]
    beta_assets = [
        {
            "name": "update-bundle-3.3.0-beta.2.zip",
            "browser_download_url": "https://dl.test/beta/bundle.zip",
        },
        {
            "name": "update-bundle-3.3.0-beta.2.zip.sha256",
            "browser_download_url": "https://dl.test/beta/bundle.sha256",
        },
        {
            "name": "update-bundle-3.3.0-beta.2.zip.sig",
            "browser_download_url": "https://dl.test/beta/bundle.sig",
        },
    ]
    return [
        {
            "tag_name": "3.3.0-beta.2",
            "prerelease": True,
            "draft": False,
            "body": "beta notes",
            "published_at": "2026-07-01T00:00:00Z",
            "assets": beta_assets,
        },
        {
            "tag_name": "3.2.0",
            "prerelease": False,
            "draft": False,
            "body": "stable notes",
            "published_at": "2026-06-01T00:00:00Z",
            "assets": stable_assets,
        },
    ]


def _make_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _seed_schema_db(path: Path, version: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "  id INTEGER PRIMARY KEY,"
            "  version INTEGER NOT NULL"
            ")"
        )
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, ?)",
            (version,),
        )


def _read_schema_db(path: Path) -> int:
    with sqlite3.connect(path) as conn:
        return conn.execute(
            "SELECT version FROM schema_version WHERE id = 1"
        ).fetchone()[0]


def _default_handler(bundle_bytes: bytes, sha_hex: str, sig_b64: str | None = None):
    """路由 GitHub API 与下载 URL 到对应的响应。"""
    signature = sig_b64 if sig_b64 is not None else _sign_bytes(bundle_bytes)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "api.github.com" in url and "/releases" in url:
            return httpx.Response(200, json=_releases_payload(bundle_bytes, sha_hex))
        if url.endswith("bundle.zip"):
            return httpx.Response(
                200,
                content=bundle_bytes,
                headers={"content-length": str(len(bundle_bytes))},
            )
        if url.endswith("bundle.sha256"):
            return httpx.Response(200, text=sha_hex + "\n")
        if url.endswith("bundle.sig"):
            return httpx.Response(200, text=signature + "\n")
        return httpx.Response(404)

    return handler


@pytest.fixture
def bundle():
    data = _make_bundle("3.3.0-beta.2")
    return data, hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# _parse_semver / _is_newer
# ---------------------------------------------------------------------------


class TestSemver:
    def test_parse_strips_v_prefix(self):
        assert str(_parse_semver("v3.3.0")) == "3.3.0"

    def test_parse_invalid_returns_none(self):
        assert _parse_semver("DEV_VERSION") is None

    def test_is_newer_true(self):
        assert _is_newer("3.3.0", "3.2.0") is True

    def test_is_newer_false_when_equal(self):
        assert _is_newer("3.2.0", "3.2.0") is False

    def test_is_newer_false_when_unparseable(self):
        assert _is_newer("3.3.0", "DEV_VERSION") is False


# ---------------------------------------------------------------------------
# check_update
# ---------------------------------------------------------------------------


class TestCheckUpdate:
    @pytest.mark.asyncio
    async def test_stable_channel_has_update(self, tmp_path, bundle):
        data, sha = bundle
        client = _make_client(_default_handler(data, sha))
        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            client=client,
        )
        res = await up.check_update("stable")
        assert res.has_update is True
        assert res.latest == "3.2.0"  # stable channel ignores the beta prerelease
        assert res.is_prerelease is False
        assert res.bundle_url == "https://dl.test/stable/bundle.zip"

    @pytest.mark.asyncio
    async def test_beta_channel_picks_prerelease(self, tmp_path, bundle):
        data, sha = bundle
        client = _make_client(_default_handler(data, sha))
        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            client=client,
        )
        res = await up.check_update("beta")
        assert res.latest == "3.3.0-beta.2"
        assert res.is_prerelease is True
        assert res.has_update is True

    @pytest.mark.asyncio
    async def test_no_update_when_current_is_latest(self, tmp_path, bundle):
        data, sha = bundle
        client = _make_client(_default_handler(data, sha))
        up = Updater(
            root=tmp_path / "u",
            current_version="3.2.0",
            image_version="3.3.0-beta.1",
            client=client,
        )
        res = await up.check_update("stable")
        assert res.has_update is False

    @pytest.mark.asyncio
    async def test_network_error_is_graceful(self, tmp_path):
        def handler(request):
            raise httpx.ConnectError("boom")

        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            client=_make_client(handler),
        )
        res = await up.check_update("stable")
        assert res.has_update is False
        assert res.error is not None

    @pytest.mark.asyncio
    async def test_force_bypasses_the_result_cache(self, tmp_path, bundle):
        """A user-initiated check must re-fetch; the 15-min cache only serves
        the passive auto-check so repeated clicks don't feel like a no-op."""
        data, sha = bundle
        calls = {"n": 0}
        inner = _default_handler(data, sha)

        def handler(request):
            calls["n"] += 1
            return inner(request)

        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            client=_make_client(handler),
        )
        await up.check_update("stable")
        await up.check_update("stable")  # within TTL → served from cache
        assert calls["n"] == 1
        await up.check_update("stable", force=True)  # force → re-fetch
        assert calls["n"] == 2


# ---------------------------------------------------------------------------
# apply_update
# ---------------------------------------------------------------------------


def _updater_for_apply(tmp_path, data, sha, current="3.1.0", image="3.3.0-beta.1"):
    return Updater(
        root=tmp_path / "u",
        current_version=current,
        image_version=image,
        dependency_syncer=lambda unpacked: None,
        client=_make_client(_default_handler(data, sha)),
        pubkey_path=_write_test_pubkey(tmp_path),
    )


class TestApplyUpdate:
    @pytest.mark.asyncio
    async def test_success_promotes_and_writes_applied(self, tmp_path, bundle):
        data, sha = bundle
        up = _updater_for_apply(tmp_path, data, sha)
        res = await up.apply_update("beta")
        assert res.success is True
        assert res.restart_required is True
        assert res.version == "3.3.0-beta.2"

        current = tmp_path / "u" / "current"
        assert (current / "manifest.json").exists()
        applied = json.loads((tmp_path / "u" / "applied.json").read_text())
        assert applied["version"] == "3.3.0-beta.2"
        assert applied["sha256"] == sha
        assert applied["lockfile_sha256"]

    @pytest.mark.asyncio
    async def test_success_snapshots_db_and_records_schema(self, tmp_path, bundle):
        data, sha = bundle
        db_path = tmp_path / "data" / "data.db"
        _seed_schema_db(db_path, 7)
        (tmp_path / "data" / "data.db-wal").write_bytes(b"wal")
        (tmp_path / "data" / "data.db-shm").write_bytes(b"shm")
        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            data_db=db_path,
            dependency_syncer=lambda unpacked: None,
            client=_make_client(_default_handler(data, sha)),
            pubkey_path=_write_test_pubkey(tmp_path),
        )

        res = await up.apply_update("beta")

        assert res.success is True
        applied = json.loads((tmp_path / "u" / "applied.json").read_text())
        assert applied["schema_version_before"] == 7
        # schema_version_after 在 apply 时不可知（迁移下次启动才跑），不得记录
        assert "schema_version_after" not in applied
        backup_db = tmp_path / "u" / applied["db_backup"]["path"]
        assert _read_schema_db(backup_db) == 7
        # backup API 快照是独立一致文件，不携带活库的 -wal/-shm 边车
        assert not (backup_db.parent / "data.db-wal").exists()
        assert not (backup_db.parent / "data.db-shm").exists()

    @pytest.mark.asyncio
    async def test_dependency_sync_failure_aborts_without_promote(
        self, tmp_path, bundle
    ):
        data, sha = bundle

        def fail_sync(unpacked: Path) -> None:
            raise RuntimeError("uv sync failed")

        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            dependency_syncer=fail_sync,
            client=_make_client(_default_handler(data, sha)),
            pubkey_path=_write_test_pubkey(tmp_path),
        )

        res = await up.apply_update("beta")

        assert res.success is False
        assert "uv sync failed" in res.message
        assert not (tmp_path / "u" / "current").exists()
        assert not (tmp_path / "u" / "applied.json").exists()

    @pytest.mark.asyncio
    async def test_sha_mismatch_aborts_without_promote(self, tmp_path, bundle):
        data, _ = bundle
        wrong_sha = "0" * 64
        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            client=_make_client(_default_handler(data, wrong_sha)),
        )
        res = await up.apply_update("beta")
        assert res.success is False
        assert "sha256" in res.message.lower()
        assert not (tmp_path / "u" / "current").exists()
        assert not (tmp_path / "u" / "applied.json").exists()

    @pytest.mark.asyncio
    async def test_bad_signature_aborts_without_promote(self, tmp_path, bundle):
        data, sha = bundle
        # 用错误密钥签名：sha256 校验通过但验签必失败
        wrong_key = Ed25519PrivateKey.generate()
        bad_sig = base64.b64encode(wrong_key.sign(data)).decode()
        up = Updater(
            root=tmp_path / "u",
            current_version="3.1.0",
            image_version="3.3.0-beta.1",
            dependency_syncer=lambda unpacked: None,
            client=_make_client(_default_handler(data, sha, sig_b64=bad_sig)),
            pubkey_path=_write_test_pubkey(tmp_path),
        )
        res = await up.apply_update("beta")
        assert res.success is False
        assert "signature" in res.message.lower()
        assert not (tmp_path / "u" / "current").exists()
        assert not (tmp_path / "u" / "applied.json").exists()

    @pytest.mark.asyncio
    async def test_apply_retains_verified_bundle_for_boot(self, tmp_path, bundle):
        data, sha = bundle
        up = _updater_for_apply(tmp_path, data, sha)
        res = await up.apply_update("beta")
        assert res.success is True
        # boot_overlay 每次启动都要用留存的已验签 zip + 签名重新验签
        assert (tmp_path / "u" / "bundle.zip").read_bytes() == data
        assert (tmp_path / "u" / "bundle.zip.sig").exists()

    @pytest.mark.asyncio
    async def test_incompatible_min_image_version_aborts(self, tmp_path):
        data = _make_bundle("3.3.0-beta.2", min_image_version="9.9.9")
        sha = hashlib.sha256(data).hexdigest()
        up = _updater_for_apply(tmp_path, data, sha, image="3.3.0-beta.1")
        res = await up.apply_update("beta")
        assert res.success is False
        assert "too old" in res.message.lower()
        assert not (tmp_path / "u" / "current").exists()

    @pytest.mark.asyncio
    async def test_second_apply_moves_current_to_backup(self, tmp_path, bundle):
        data, sha = bundle
        up = _updater_for_apply(tmp_path, data, sha)
        await up.apply_update("beta")
        # 应用第二次（复用同一 bundle）：旧 current 应被移到 backup。
        up._cache = None
        await up.apply_update("beta")
        assert (tmp_path / "u" / "backup").exists()
        assert (tmp_path / "u" / "current" / "manifest.json").exists()


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------


class TestRollback:
    @pytest.mark.asyncio
    async def test_rollback_swaps_backup_into_current(self, tmp_path):
        root = tmp_path / "u"
        current = root / "current"
        backup = root / "backup"
        current.mkdir(parents=True)
        backup.mkdir(parents=True)
        (current / "manifest.json").write_text(json.dumps({"version": "3.3.0"}))
        (backup / "manifest.json").write_text(json.dumps({"version": "3.2.0"}))

        up = Updater(root=root, current_version="3.3.0", image_version="3.1.0")
        res = await up.rollback()
        assert res.success is True
        assert res.version == "3.2.0"
        # current now holds the old backup content
        cur = json.loads((current / "manifest.json").read_text())
        assert cur["version"] == "3.2.0"
        applied = json.loads((root / "applied.json").read_text())
        assert applied["version"] == "3.2.0"

    @pytest.mark.asyncio
    async def test_rollback_restores_db_snapshot(self, tmp_path):
        root = tmp_path / "u"
        current = root / "current"
        backup = root / "backup"
        current.mkdir(parents=True)
        backup.mkdir(parents=True)
        (current / "manifest.json").write_text(json.dumps({"version": "3.3.0"}))
        (backup / "manifest.json").write_text(json.dumps({"version": "3.2.0"}))
        db_path = tmp_path / "data" / "data.db"
        _seed_schema_db(db_path, 9)
        backup_db = root / "db-backup" / "data.db"
        _seed_schema_db(backup_db, 4)
        (root / "applied.json").write_text(
            json.dumps(
                {
                    "version": "3.3.0",
                    "schema_version_before": 4,
                    "db_backup": {"path": "db-backup/data.db"},
                }
            )
        )

        up = Updater(
            root=root,
            current_version="3.3.0",
            image_version="3.1.0",
            data_db=db_path,
        )
        res = await up.rollback()

        assert res.success is True
        # schema 自 apply 后前进过（4 -> 9），旧代码读不了新库，必须还原快照
        assert _read_schema_db(db_path) == 4
        applied = json.loads((root / "applied.json").read_text())
        assert applied["schema_version_before"] == 9
        assert applied["schema_version_after"] == 4
        # 快照目录用后即焚，避免下一轮回滚误还原陈旧快照
        assert not (root / "db-backup").exists()

    @pytest.mark.asyncio
    async def test_rollback_keeps_live_db_when_schema_unchanged(self, tmp_path):
        root = tmp_path / "u"
        current = root / "current"
        backup = root / "backup"
        current.mkdir(parents=True)
        backup.mkdir(parents=True)
        (current / "manifest.json").write_text(json.dumps({"version": "3.3.0"}))
        (backup / "manifest.json").write_text(json.dumps({"version": "3.2.0"}))
        db_path = tmp_path / "data" / "data.db"
        _seed_schema_db(db_path, 4)
        backup_db = root / "db-backup" / "data.db"
        _seed_schema_db(backup_db, 3)
        (root / "applied.json").write_text(
            json.dumps(
                {
                    "version": "3.3.0",
                    "schema_version_before": 4,
                    "db_backup": {"path": "db-backup/data.db"},
                }
            )
        )

        up = Updater(
            root=root,
            current_version="3.3.0",
            image_version="3.1.0",
            data_db=db_path,
        )
        res = await up.rollback()

        assert res.success is True
        # schema 没变：保留活库，不得用快照抹掉更新后写入的数据
        assert _read_schema_db(db_path) == 4

    @pytest.mark.asyncio
    async def test_second_rollback_ignores_leftover_backup_dir(self, tmp_path):
        root = tmp_path / "u"
        current = root / "current"
        backup = root / "backup"
        current.mkdir(parents=True)
        backup.mkdir(parents=True)
        (current / "manifest.json").write_text(json.dumps({"version": "3.3.0"}))
        (backup / "manifest.json").write_text(json.dumps({"version": "3.2.0"}))
        db_path = tmp_path / "data" / "data.db"
        _seed_schema_db(db_path, 9)
        # 上一轮更新遗留的快照目录；本轮 applied.json 没有 db_backup 记录
        stale_backup = root / "db-backup" / "data.db"
        _seed_schema_db(stale_backup, 3)
        (root / "applied.json").write_text(
            json.dumps(
                {
                    "version": "3.3.0",
                    "rolled_back": True,
                    "schema_version_before": 5,
                }
            )
        )

        up = Updater(
            root=root,
            current_version="3.3.0",
            image_version="3.1.0",
            data_db=db_path,
        )
        res = await up.rollback()

        assert res.success is True
        # 不得回退到磁盘残留的陈旧快照
        assert _read_schema_db(db_path) == 9

    @pytest.mark.asyncio
    async def test_rollback_refuses_unknown_future_schema(self, tmp_path):
        root = tmp_path / "u"
        current = root / "current"
        backup = root / "backup"
        current.mkdir(parents=True)
        backup.mkdir(parents=True)
        (current / "manifest.json").write_text(json.dumps({"version": "3.3.0"}))
        (backup / "manifest.json").write_text(json.dumps({"version": "3.2.0"}))
        db_path = tmp_path / "data" / "data.db"
        _seed_schema_db(db_path, 999)

        up = Updater(
            root=root,
            current_version="3.3.0",
            image_version="3.1.0",
            data_db=db_path,
        )
        with patch("module.update.updater.CURRENT_SCHEMA_VERSION", 14):
            res = await up.rollback()

        assert res.success is False
        assert "schema" in res.message
        assert (backup / "manifest.json").exists()
        cur = json.loads((current / "manifest.json").read_text())
        assert cur["version"] == "3.3.0"

    @pytest.mark.asyncio
    async def test_rollback_without_backup_reverts_to_image(self, tmp_path):
        root = tmp_path / "u"
        current = root / "current"
        current.mkdir(parents=True)
        (current / "manifest.json").write_text(json.dumps({"version": "3.3.0"}))
        (root / "applied.json").write_text(json.dumps({"version": "3.3.0"}))

        up = Updater(root=root, current_version="3.3.0", image_version="3.2.5")
        res = await up.rollback()
        assert res.success is True
        assert res.version == "3.2.5"
        assert not current.exists()
        assert not (root / "applied.json").exists()


# ---------------------------------------------------------------------------
# boot_overlay
# ---------------------------------------------------------------------------


class TestBootOverlay:
    def _seed(self, tmp_path, overlay_version, sign=True, stage_venv=True):
        """构造一个假的 /app 布局 + 已验签覆盖层。返回相关路径。

        module 树与前端 dist 现在从已验签的 bundle.zip 解包，不再从 current/
        复制；staged .venv 仍来自 current/.venv。
        """
        app = tmp_path / "app"
        (app / "module").mkdir(parents=True)
        (app / "module" / "old.txt").write_text("image module")
        (app / "dist").mkdir(parents=True)
        (app / "dist" / "old.html").write_text("image dist")

        updates = app / "config" / "updates"
        updates.mkdir(parents=True)
        bundle_bytes = _make_bundle(overlay_version)
        (updates / "bundle.zip").write_bytes(bundle_bytes)
        sig = _sign_bytes(bundle_bytes)
        if not sign:
            # 篡改签名：验签必失败
            sig = base64.b64encode(b"\x00" * 64).decode()
        (updates / "bundle.zip.sig").write_text(sig)
        (updates / "applied.json").write_text(json.dumps({"version": overlay_version}))

        if stage_venv:
            current = updates / "current"
            (current / ".venv").mkdir(parents=True)
            (current / ".venv" / "pyvenv.cfg").write_text("overlay venv")

        image_version_path = app / "IMAGE_VERSION"
        image_version_path.write_text("3.3.0")
        baseline_lock = app / "uv.lock"
        baseline_lock.write_text("baseline lock\n")
        pubkey = _write_test_pubkey(tmp_path)
        return app, updates, image_version_path, baseline_lock, pubkey

    def test_applies_overlay_when_newer(self, tmp_path):
        import boot_overlay

        app, updates, ivp, lock, pubkey = self._seed(tmp_path, "3.4.0")
        applied = boot_overlay.apply_overlay(
            app_root=app,
            updates_root=updates,
            image_version_path=ivp,
            baseline_lock=lock,
            pubkey_path=pubkey,
        )
        assert applied is True
        # module 树来自 zip 内 backend/src/module/__marker__.txt
        assert (app / "module" / "__marker__.txt").exists()
        assert not (app / "module" / "old.txt").exists()  # tree replaced, not merged
        assert (app / "dist" / "index.html").exists()
        assert (app / ".venv" / "pyvenv.cfg").read_text() == "overlay venv"

    def test_rejects_overlay_with_bad_signature(self, tmp_path):
        import boot_overlay

        app, updates, ivp, lock, pubkey = self._seed(tmp_path, "3.4.0", sign=False)
        applied = boot_overlay.apply_overlay(
            app_root=app,
            updates_root=updates,
            image_version_path=ivp,
            baseline_lock=lock,
            pubkey_path=pubkey,
        )
        assert applied is False
        assert (app / "module" / "old.txt").exists()  # image kept
        # 验签失败的覆盖层被清除
        assert not (updates / "bundle.zip").exists()

    def test_rejects_legacy_overlay_without_bundle(self, tmp_path):
        """只有 applied.json + current/（旧格式、无签名 bundle）必须拒绝。"""
        import boot_overlay

        app = tmp_path / "app"
        (app / "module").mkdir(parents=True)
        (app / "module" / "old.txt").write_text("image module")
        updates = app / "config" / "updates"
        current = updates / "current" / "backend" / "src" / "module"
        current.mkdir(parents=True)
        (current / "evil.txt").write_text("attacker module")
        (updates / "applied.json").write_text(json.dumps({"version": "9.9.9"}))
        ivp = app / "IMAGE_VERSION"
        ivp.write_text("3.3.0")

        applied = boot_overlay.apply_overlay(
            app_root=app,
            updates_root=updates,
            image_version_path=ivp,
            baseline_lock=app / "uv.lock",
            pubkey_path=_write_test_pubkey(tmp_path),
        )
        assert applied is False
        assert (
            app / "module" / "old.txt"
        ).exists()  # image kept, attacker tree ignored
        assert not (updates / "applied.json").exists()  # unsigned overlay cleared

    def test_skips_and_clears_overlay_when_image_newer(self, tmp_path):
        import boot_overlay

        app, updates, ivp, lock, pubkey = self._seed(tmp_path, "3.2.0")  # < image
        applied = boot_overlay.apply_overlay(
            app_root=app,
            updates_root=updates,
            image_version_path=ivp,
            baseline_lock=lock,
            pubkey_path=pubkey,
        )
        assert applied is False
        assert (app / "module" / "old.txt").exists()  # image kept
        assert not (updates / "applied.json").exists()  # stale marker cleared
        assert not (updates / "bundle.zip").exists()

    def test_no_applied_json_is_noop(self, tmp_path):
        import boot_overlay

        app = tmp_path / "app"
        (app / "module").mkdir(parents=True)
        updates = app / "config" / "updates"
        updates.mkdir(parents=True)
        ivp = app / "IMAGE_VERSION"
        ivp.write_text("3.3.0")
        applied = boot_overlay.apply_overlay(
            app_root=app,
            updates_root=updates,
            image_version_path=ivp,
            baseline_lock=app / "uv.lock",
            pubkey_path=_write_test_pubkey(tmp_path),
        )
        assert applied is False


# ---------------------------------------------------------------------------
# API contract: path + verb + auth-gated
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    return app


@pytest.fixture
def authed_client(app):
    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(app):
    return TestClient(app)


class TestUpdateApiContract:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_check_requires_auth(self, unauthed_client):
        assert unauthed_client.get("/api/v1/update/check").status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_apply_requires_auth(self, unauthed_client):
        assert unauthed_client.post("/api/v1/update/apply").status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_rollback_requires_auth(self, unauthed_client):
        assert unauthed_client.post("/api/v1/update/rollback").status_code == 401

    def test_check_get(self, authed_client):
        from module.update.updater import UpdateCheckResult

        async def fake_check(channel="stable", *, force=False):
            return UpdateCheckResult(current="3.2.0", latest="3.3.0", has_update=True)

        with patch("module.api.update.updater.check_update", side_effect=fake_check):
            resp = authed_client.get("/api/v1/update/check?channel=beta")
        assert resp.status_code == 200
        assert resp.json()["has_update"] is True

    def test_apply_post_schedules_restart(self, authed_client):
        from module.update.updater import ApplyResult

        async def fake_apply(channel="stable"):
            return ApplyResult(
                success=True, version="3.3.0", restart_required=True, message="ok"
            )

        with (
            patch("module.api.update.updater.apply_update", side_effect=fake_apply),
            patch("module.api.update.schedule_restart") as sched,
        ):
            resp = authed_client.post("/api/v1/update/apply")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        sched.assert_called_once()

    def test_rollback_post_schedules_restart(self, authed_client):
        from module.update.updater import ApplyResult

        async def fake_rollback():
            return ApplyResult(
                success=True, version="3.2.0", restart_required=True, message="ok"
            )

        with (
            patch("module.api.update.updater.rollback", side_effect=fake_rollback),
            patch("module.api.update.schedule_restart") as sched,
        ):
            resp = authed_client.post("/api/v1/update/rollback")
        assert resp.status_code == 200
        sched.assert_called_once()

    def test_apply_failure_returns_400(self, authed_client):
        from module.update.updater import ApplyResult

        async def fake_apply(channel="stable"):
            return ApplyResult(success=False, message="no update available")

        with (
            patch("module.api.update.updater.apply_update", side_effect=fake_apply),
            patch("module.api.update.schedule_restart") as sched,
        ):
            resp = authed_client.post("/api/v1/update/apply")
        assert resp.status_code == 400
        sched.assert_not_called()

    def test_request_restart_writes_entrypoint_sentinel(self, tmp_path):
        from module.api import update as update_api

        sentinel = tmp_path / "config" / "updates" / ".restart"
        with (
            patch("module.api.update.RESTART_SENTINEL", sentinel),
            patch("module.api.update.os.kill") as kill,
        ):
            update_api._request_restart()

        assert sentinel.exists()
        kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_restart_retains_task_reference(self):
        from module.api import update as update_api

        update_api._RESTART_TASKS.clear()
        with (
            patch("module.api.update._RESTART_DELAY_SECONDS", 0),
            patch("module.api.update._request_restart"),
        ):
            update_api.schedule_restart()
            assert len(update_api._RESTART_TASKS) == 1
            await asyncio.gather(*list(update_api._RESTART_TASKS))
            await asyncio.sleep(0)
        assert len(update_api._RESTART_TASKS) == 0
