"""前端挂载点的实物：内置插件声明的 web/ 文件齐全，示例插件「手动选种」可用。"""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ab_sdk import points
from module.api import v1
from module.api.deps import get_context
from module.models.config import Plugins
from module.plugin.loader import BUILTIN_ROOT, discover
from module.plugin.manager import PluginManager
from module.plugin.registry import ExtensionPoint, ExtensionRegistry
from module.security.api import get_current_user

EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "plugins"


def _discover(local_root: Path, builtin_root: Path = BUILTIN_ROOT):
    candidates, errors = discover(
        builtin_root=builtin_root,
        local_root=local_root,
        entry_point_group="ab-test-none",
    )
    assert errors == []
    return candidates


POINT = ExtensionPoint(points.API_ROUTER, "provider", "插件 REST 路由", scoped=True)


def test_builtin_ui_entries_exist_on_disk():
    declared = [
        (c.manifest.id, ui.entry)
        for c in _discover(BUILTIN_ROOT / "__missing__")
        for ui in c.manifest.ui
    ]
    assert ("hardlink", "web/index.js") in declared
    for plugin_id, entry in declared:
        assert (BUILTIN_ROOT / plugin_id / entry).is_file()


@pytest.fixture
async def manager(tmp_path):
    settings_obj = SimpleNamespace(
        plugins=Plugins(allow_unsigned=True, enabled={"manual-pick": True})
    )
    registry = ExtensionRegistry()
    registry.declare(POINT)
    mgr = PluginManager(
        settings_obj,
        registry=registry,
        discover_fn=lambda: (_discover(EXAMPLES, tmp_path / "none"), []),
        data_root=tmp_path,
    )
    await mgr.start()
    yield mgr
    await mgr.stop()


async def test_manual_pick_routes_store_pick_and_publish_event(manager):
    from module.core.plugin_routes import PluginRoutes

    [status] = manager.statuses()
    assert status.state == "active"
    assert [(pid, ui.slot) for pid, ui in manager.ui_slots()] == [
        ("manual-pick", "bangumi.detail.tab")
    ]
    assert (manager.web_dir("manual-pick") / "index.js").is_file()  # type: ignore[operator]

    routes = PluginRoutes(manager.registry, manager.breaker)
    routes.sync()
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    app.dependency_overrides[get_context] = lambda: SimpleNamespace(
        plugins=manager, plugin_routes=routes
    )

    async def user():
        return "testuser"

    app.dependency_overrides[get_current_user] = user
    client = TestClient(app)

    seen: list[Any] = []
    manager.bus.subscribe("manual-pick.picked", seen.append)
    base = "/api/v1/plugins/manual-pick/picks/3"
    assert client.get(base).json() == {"torrent_id": None}
    assert client.put(base, json={"torrent_id": 9}).json() == {"torrent_id": 9}
    assert client.get(base).json() == {"torrent_id": 9}
    await manager.bus.drain()
    assert [(e.bangumi_id, e.torrent_id) for e in seen] == [(3, 9)]
