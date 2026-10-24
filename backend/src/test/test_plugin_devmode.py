"""dev_mode：本地插件文件变更后自动重载。"""

import asyncio
import shutil
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from module.models.config import Plugins
from module.plugin.loader import discover
from module.plugin.manager import PluginManager
from module.plugin.registry import ExtensionPoint

MANIFEST = """
[plugin]
id = "dev"
name = "Dev"
version = "1.0.0"
sdk = ">=0.1,<1"
entry = "dev:DevPlugin"
"""

SOURCE = """
from ab_sdk import Plugin, provider


class DevPlugin(Plugin):
    @provider("rename_strategy", id="dev")
    def strategy(self):
        return "{value}"
"""


def write_source(plugin_dir: Path, value: str) -> None:
    (plugin_dir / "dev.py").write_text(SOURCE.format(value=value))


@pytest.fixture
def plugin_dir(tmp_path):
    path = tmp_path / "local" / "dev"
    path.mkdir(parents=True)
    (path / "plugin.toml").write_text(MANIFEST)
    write_source(path, "v1")
    return path


def make_manager(tmp_path: Path, **plugins_conf) -> PluginManager:
    manager = PluginManager(
        SimpleNamespace(
            plugins=Plugins(allow_unsigned=True, enabled={"dev": True}, **plugins_conf)
        ),
        discover_fn=lambda: discover(
            builtin_root=tmp_path / "none",
            local_root=tmp_path / "local",
            entry_point_group="ab-test-none",
        ),
        data_root=tmp_path / "data",
        watch_interval=0.02,
    )
    manager.registry.declare(ExtensionPoint("rename_strategy", "provider"))
    return manager


def strategy(manager: PluginManager) -> str | None:
    entry = manager.registry.providers("rename_strategy").get("dev")
    return entry.factory() if entry else None


async def eventually(check: Callable[[], bool], timeout: float = 3.0) -> None:
    async with asyncio.timeout(timeout):
        while not check():
            await asyncio.sleep(0.02)


async def test_dev_mode_reloads_local_plugin_when_source_changes(tmp_path, plugin_dir):
    manager = make_manager(tmp_path, dev_mode=True)
    await manager.start()
    assert strategy(manager) == "v1"

    write_source(plugin_dir, "version-2")

    await eventually(lambda: strategy(manager) == "version-2")
    await manager.stop()


async def test_dev_mode_recovers_plugin_that_failed_to_load(tmp_path, plugin_dir):
    write_source(plugin_dir, "v1")
    (plugin_dir / "dev.py").write_text("def broken(:\n")
    manager = make_manager(tmp_path, dev_mode=True)
    await manager.start()
    assert manager.statuses()[0].state == "error"

    write_source(plugin_dir, "fixed")

    await eventually(lambda: strategy(manager) == "fixed")
    assert manager.statuses()[0].state == "active"
    await manager.stop()


async def test_changes_are_ignored_without_dev_mode(tmp_path, plugin_dir):
    manager = make_manager(tmp_path)
    await manager.start()

    write_source(plugin_dir, "version-2")
    await asyncio.sleep(0.2)

    assert strategy(manager) == "v1"
    await manager.stop()


async def test_watcher_follows_dev_mode_setting(tmp_path, plugin_dir):
    manager = make_manager(tmp_path)
    await manager.start()
    manager._settings.plugins.dev_mode = True
    await manager.apply_settings()

    write_source(plugin_dir, "version-2")

    await eventually(lambda: strategy(manager) == "version-2")
    manager._settings.plugins.dev_mode = False
    await manager.apply_settings()
    write_source(plugin_dir, "version-3")
    await asyncio.sleep(0.2)
    assert strategy(manager) == "version-2"
    await manager.stop()


async def test_reload_picks_up_new_code_without_config_change(tmp_path, plugin_dir):
    manager = make_manager(tmp_path)
    await manager.start()
    write_source(plugin_dir, "version-2")

    await manager.reload("dev")

    assert strategy(manager) == "version-2"
    await manager.stop()


async def test_reload_of_removed_plugin_deactivates_it(tmp_path, plugin_dir):
    manager = make_manager(tmp_path)
    await manager.start()
    assert strategy(manager) == "v1"
    shutil.rmtree(plugin_dir)

    await manager.reload("dev")

    assert strategy(manager) is None
    assert manager.statuses() == []
    await manager.stop()
