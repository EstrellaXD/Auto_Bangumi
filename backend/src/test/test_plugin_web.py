"""前端插件（第 3.8 节）：UI 挂载点列表、web/ 静态资源与 SPA 的 CSP。"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import main
from ab_sdk import Plugin
from module.api import v1
from module.api.deps import get_context
from module.models.config import Plugins
from module.plugin.loader import PluginCandidate
from module.plugin.manager import PluginManager
from module.plugin.manifest import parse_manifest
from module.security.api import get_current_user

MANIFEST = """
[plugin]
id = "{id}"
name = "Demo"
version = "1.0.0"
sdk = ">=0.1,<1"
entry = "x:Y"

[[plugin.ui]]
slot = "bangumi.detail.tab"
element = "ab-plugin-{id}"
entry = "web/index.js"
title = {{ zh-CN = "演示", en-US = "Demo" }}
"""


class DemoPlugin(Plugin):
    pass


def candidate(root: Path, plugin_id: str = "demo") -> PluginCandidate:
    web = root / plugin_id / "web"
    web.mkdir(parents=True)
    (web / "index.js").write_text("export const ok = 1;\n")
    (web / "style.css").write_text(":host{}\n")
    (root / plugin_id / "plugin.toml").write_text("secret = 1\n")
    return PluginCandidate(
        manifest=parse_manifest(MANIFEST.format(id=plugin_id)),
        source="builtin",
        load=lambda: DemoPlugin,
        root=root / plugin_id,
    )


@pytest.fixture
async def manager(tmp_path):
    settings_obj = SimpleNamespace(plugins=Plugins(enabled={"off": False}))
    candidates = [candidate(tmp_path, "demo"), candidate(tmp_path, "off")]
    mgr = PluginManager(
        settings_obj,
        discover_fn=lambda: (candidates, []),
        data_root=tmp_path / "data",
    )
    await mgr.start()
    yield mgr
    await mgr.stop()


@pytest.fixture
def client(manager):
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    app.dependency_overrides[get_context] = lambda: SimpleNamespace(plugins=manager)

    async def user():
        return "testuser"

    app.dependency_overrides[get_current_user] = user
    return TestClient(app)


class TestManager:
    async def test_ui_slots_and_web_dir_only_for_active_plugins(
        self, manager, tmp_path
    ):
        assert [(pid, ui.element) for pid, ui in manager.ui_slots()] == [
            ("demo", "ab-plugin-demo")
        ]
        assert manager.web_dir("demo") == tmp_path / "demo" / "web"
        assert manager.web_dir("off") is None

        await manager._deactivate("demo")
        assert manager.ui_slots() == []
        assert manager.web_dir("demo") is None

    async def test_ui_slots_element_owned_by_longest_matching_plugin_id(self, tmp_path):
        # 「foo」的命名空间前缀也匹配 ab-plugin-foo-bar，但该名字属于更长的 id「foo-bar」
        foo = candidate(tmp_path, "foo")
        foo.manifest.ui[0].element = "ab-plugin-foo-bar"
        foo_bar = candidate(tmp_path, "foo-bar")
        mgr = PluginManager(
            SimpleNamespace(plugins=Plugins()),
            discover_fn=lambda: ([foo, foo_bar], []),
            data_root=tmp_path / "data",
        )
        await mgr.start()
        assert [(pid, ui.element) for pid, ui in mgr.ui_slots()] == [
            ("foo-bar", "ab-plugin-foo-bar")
        ]
        await mgr.stop()


class TestApi:
    def test_list_ui_slots(self, client):
        resp = client.get("/api/v1/plugins/ui")
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "plugin_id": "demo",
                "slot": "bangumi.detail.tab",
                "element": "ab-plugin-demo",
                "entry": "web/index.js",
                "title": {"zh-CN": "演示", "en-US": "Demo"},
            }
        ]

    @pytest.mark.parametrize(
        "path, media_type",
        [("index.js", "text/javascript"), ("style.css", "text/css")],
    )
    def test_serves_web_file_with_mime_type(self, client, path, media_type):
        resp = client.get(f"/api/v1/plugins/demo/web/{path}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(media_type)
        assert resp.headers["cache-control"] == "no-cache"

    @pytest.mark.parametrize(
        "url",
        [
            # httpx 会把字面的 ../ 规范化掉，用百分号编码让它原样到达路由
            "/api/v1/plugins/demo/web/%2e%2e%2fplugin.toml",
            # 绝对路径会让 root / path 直接变成该路径
            "/api/v1/plugins/demo/web//etc/hosts",
            "/api/v1/plugins/demo/web/missing.js",
            "/api/v1/plugins/demo/web/",
            "/api/v1/plugins/off/web/index.js",
            "/api/v1/plugins/unknown/web/index.js",
        ],
    )
    def test_outside_web_dir_or_inactive_is_404(self, client, url):
        assert client.get(url).status_code == 404

    def test_requires_auth(self, client):
        del client.app.dependency_overrides[get_current_user]
        assert client.get("/api/v1/plugins/demo/web/index.js").status_code == 401
        assert client.get("/api/v1/plugins/ui").status_code == 401


class TestSpaCsp:
    @pytest.mark.parametrize("path", ["", "bangumi", "sw.js"])
    def test_spa_responses_carry_csp(self, tmp_path, path):
        for name in ("assets", "images"):
            (tmp_path / name).mkdir()
        (tmp_path / "index.html").write_text("<html></html>")
        (tmp_path / "sw.js").write_text("")
        app = FastAPI()
        main.mount_webui(app, tmp_path)
        resp = TestClient(app).get(f"/{path}")
        assert resp.status_code == 200
        assert resp.headers["content-security-policy"] == "script-src 'self'"
