"""用户固定来源的本地更新，不改签名市场的信任规则。"""

import asyncio
import hashlib
import io
import json
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from module.conf import settings
from module.database import Database
from module.plugin import host, loader, local_updates, maintenance
from module.plugin.local_updates import HostPluginUpdates, unpack
from module.plugin.manager import PluginManager


def package(version="2.0.0", *, bad_setup=False, plugin_id="demo", sdk=">=0.7,<1"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "plugin.toml",
            f'[plugin]\nid="{plugin_id}"\nname="Demo"\nversion="{version}"\nsdk="{sdk}"\nentry="demo:Demo"\n',
        )
        body = "        pass\n"
        if bad_setup:
            body = """        (self.ctx.data_dir / "state").write_text("new")
        await self.ctx.kv.set("new-only", True)
        raise RuntimeError("bad release")
"""
        archive.writestr(
            "demo.py",
            "from ab_sdk import Plugin\nclass Demo(Plugin):\n    async def setup(self):\n"
            + body,
        )
    return stream.getvalue()


@pytest.fixture
async def updater(tmp_path, monkeypatch):
    local = tmp_path / "plugins" / "local"
    root = local / "demo"
    unpack(
        package("1.0.0"),
        hashlib.sha256(package("1.0.0")).hexdigest(),
        root,
        "demo",
        "1.0.0",
    )
    monkeypatch.setattr(loader, "LOCAL_ROOT", local)
    monkeypatch.setattr(settings.plugins, "allow_unsigned", True)
    monkeypatch.setattr(settings.plugins, "enabled", {"demo": True})
    monkeypatch.setattr(
        settings.plugins, "local_update_sources", {"demo": "example/demo"}
    )
    backups = tmp_path / "backups"
    monkeypatch.setattr(local_updates, "BACKUP_ROOT", backups)
    monkeypatch.setattr(maintenance, "BACKUP_ROOT", backups)
    manager = PluginManager(
        settings,
        discover_fn=lambda: loader.discover(
            builtin_root=tmp_path / "none",
            catalog_root=tmp_path / "none",
            local_root=local,
            entry_point_group="ab-test-none",
        ),
        data_root=tmp_path / "data",
    )
    await manager.start()
    scheduler = SimpleNamespace(running=True, stop_all=AsyncMock(), start_all=Mock())
    application = SimpleNamespace(
        _lifecycle_lock=asyncio.Lock(), scheduler=scheduler, plugins=manager
    )
    monkeypatch.setattr(maintenance, "_application", application)
    monkeypatch.setattr(host, "_bus", manager.bus)
    from module.notification import NotificationManager

    monkeypatch.setattr(NotificationManager, "send_event", AsyncMock())
    service = HostPluginUpdates("demo", tmp_path / "data" / "demo")
    service.data_dir.mkdir(parents=True, exist_ok=True)
    (service.data_dir / "state").write_text("old")
    yield service, manager, scheduler, root
    await manager.stop()


def github(monkeypatch, data, *, checksum=None, repository="example/demo"):
    base = f"https://github.com/{repository}/releases/download/v2.0.0/"
    name = "demo-2.0.0.zip"
    release = {
        "tag_name": "v2.0.0",
        "assets": [
            {"name": n, "browser_download_url": base + n}
            for n in [name, name + ".sha256"]
        ],
    }

    async def fetch(url, limit):
        if url.endswith("/latest"):
            return json.dumps(release).encode()
        if url.endswith(".sha256"):
            return (
                checksum if checksum is not None else hashlib.sha256(data).hexdigest()
            ).encode()
        assert url == base + name
        return data

    monkeypatch.setattr(local_updates, "fetch", fetch)


async def test_update_pins_source_and_rejects_duplicate_install(updater, monkeypatch):
    service, manager, scheduler, root = updater
    github(monkeypatch, package())
    info = await service.check()
    assert info.available and info.repository == "example/demo"
    await service.install(info.version, install_token=info.install_token)
    [status] = manager.statuses()
    assert status.version == "2.0.0" and status.state == "active"
    assert (service.data_dir / "state").read_text() == "old"
    assert scheduler.stop_all.await_count == 1
    scheduler.start_all.assert_called_once()
    with pytest.raises(ValueError, match="expired"):
        await service.install(info.version, install_token=info.install_token)
    assert not await maintenance.blocked()


async def test_loading_failure_restores_code_private_files_and_kv(updater, monkeypatch):
    service, manager, scheduler, root = updater
    github(monkeypatch, package(bad_setup=True))
    async with Database() as db:
        await db.plugin_kv.set("demo", "preserved", {"value": 1})
        await db.plugin_kv.set("other", "untouched", True)
    info = await service.check()
    with pytest.raises(RuntimeError, match="failed to load"):
        await service.install(info.version, install_token=info.install_token)
    assert (service.data_dir / "state").read_text() == "old"
    async with Database() as db:
        assert await db.plugin_kv.get("demo", "new-only") == (False, None)
        assert await db.plugin_kv.get("demo", "preserved") == (True, {"value": 1})
        assert await db.plugin_kv.get("other", "untouched") == (True, True)
    [status] = manager.statuses()
    assert status.version == "1.0.0" and status.state == "active"
    scheduler.start_all.assert_not_called()
    assert await maintenance.blocked()
    [operation] = await service_maintenance(service).operations()
    # 模拟进程中断后代码目录丢失；不依赖新版本还能加载。
    import shutil

    shutil.rmtree(root)
    await service.recover(operation.id)
    assert root.is_dir() and manager.statuses()[0].version == "1.0.0"
    assert not await maintenance.blocked()


def service_maintenance(service):
    return maintenance.HostMaintenanceService(service.plugin_id, service.data_dir)


async def test_changed_source_checksum_or_sdk_failure_never_stops_tasks(
    updater, monkeypatch
):
    service, _, scheduler, _ = updater
    github(monkeypatch, package(), checksum="0" * 64)
    info = await service.check()
    with pytest.raises(ValueError, match="checksum"):
        await service.install(info.version, install_token=info.install_token)
    scheduler.stop_all.assert_not_awaited()
    github(monkeypatch, package(sdk=">=99"))
    info = await service.check()
    with pytest.raises(ValueError, match="compatibility"):
        await service.install(info.version, install_token=info.install_token)
    scheduler.stop_all.assert_not_awaited()
    settings.plugins.local_update_sources["demo"] = "example/changed"
    with pytest.raises(ValueError, match="expired"):
        await service.install(info.version, install_token=info.install_token)


@pytest.mark.parametrize(
    "name", ["../outside.py", "/absolute.py", "C:/windows.py", "web/../../outside.py"]
)
def test_zip_traversal_rejected_before_loading(tmp_path, name):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(name, "bad")
    data = stream.getvalue()
    with pytest.raises(ValueError, match="Unsafe"):
        unpack(
            data, hashlib.sha256(data).hexdigest(), tmp_path / "stage", "demo", "2.0.0"
        )
    assert not (tmp_path / "outside.py").exists()


async def test_unconfigured_unsigned_plugins_have_no_implicit_update_source(
    updater, monkeypatch
):
    service, _, _, _ = updater
    monkeypatch.setattr(settings.plugins, "local_update_sources", {})
    fetch = AsyncMock()
    monkeypatch.setattr(local_updates, "fetch", fetch)
    with pytest.raises(ValueError, match="source"):
        await service.check()
    fetch.assert_not_awaited()
