"""P5：系统事件上总线、message_template、插件 REST 路由与 MCP 工具/资源。"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ab_sdk import Event, Plugin, hook, points, provider, subscribe
from ab_sdk.events import (
    RssFailureEvent,
    SystemEvent,
    UpdateAppliedEvent,
)
from ab_sdk.mcp import McpResource, McpTool
from ab_sdk.notify import RenderedMessage
from module.api import v1
from module.api.deps import get_context
from module.core.plugin_routes import PluginRoutes
from module.models.config import NotificationProvider as ProviderConfig
from module.models.config import Plugins
from module.notification import NotificationManager
from module.notification.inbox import InboxChanged, bump_inbox_revision
from module.notification.template import render_event
from module.plugin import host
from module.plugin.bus import EventBus
from module.plugin.loader import PluginCandidate
from module.plugin.manager import PluginManager
from module.plugin.manifest import parse_manifest
from module.plugin.registry import ExtensionRegistry, HookEntry, ProviderEntry
from module.plugin.runner import CircuitBreaker, HookRunner
from module.security.api import get_current_user


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setattr(host, "_registry", None)
    return host.get_registry()


@pytest.fixture
def bus(monkeypatch):
    bus = EventBus()
    monkeypatch.setattr(host, "_bus", bus)
    return bus


@pytest.fixture
def breaker():
    return CircuitBreaker()


@pytest.fixture
def runner(monkeypatch, registry, breaker):
    runner = HookRunner(registry, breaker)
    monkeypatch.setattr(host, "_runner", runner)
    return runner


def add(registry, point, provider_id, impl, plugin_id="ext"):
    registry.add_provider(point, ProviderEntry(plugin_id, provider_id, lambda: impl))


# ---------------------------------------------------------------- system events


class TestSystemEvents:
    def test_system_events_are_sdk_events(self):
        event = RssFailureEvent(rss_name="Feed", rss_url="http://x", error="boom")
        assert isinstance(event, Event)
        assert isinstance(event, SystemEvent)
        assert event.kind == "rss_failure"
        # 宿主旧的 import 路径仍然可用，且是同一个类
        from module.notification import RssFailureEvent as HostRssFailureEvent

        assert HostRssFailureEvent is RssFailureEvent

    def test_i18n_key_matches_frontend_and_payload_is_params(self):
        event = RssFailureEvent(rss_name="Feed", rss_url="http://x", error="boom")
        key, params = event.i18n()
        assert key == "notifications.kind.rss_failure"
        assert params == event.payload()
        failed = UpdateAppliedEvent(version="4.0.0", success=False, message="x")
        assert failed.i18n()[0] == "notifications.kind.update_failed"

    def test_plugin_defined_system_event_defaults(self):
        from dataclasses import dataclass
        from typing import ClassVar

        @dataclass(frozen=True, slots=True)
        class Synced(SystemEvent):
            kind: ClassVar[str] = "demo.synced"
            count: int

        event = Synced(count=3)
        assert event.payload() == {"count": 3}
        assert event.dedup_key() is None
        assert event.severity == "info"
        assert event.describe() == ("demo.synced", "")

    async def test_send_event_publishes_to_bus_even_when_push_disabled(self, bus):
        received: list[Event] = []
        bus.subscribe("rss_failure", received.append)
        manager = NotificationManager(load_providers=False)
        event = RssFailureEvent(rss_name="Feed", rss_url="http://x", error="boom")
        with (
            patch(
                "module.notification.manager.record_event", new_callable=AsyncMock
            ) as record,
            patch("module.notification.manager.settings") as mock_settings,
        ):
            mock_settings.notification.enable = False
            await manager.send_event(event)
        await bus.drain()
        record.assert_awaited_once_with(event)
        assert received == [event]

    async def test_send_event_publishes_even_if_inbox_write_fails(self, bus):
        received: list[Event] = []
        bus.subscribe("*", received.append)
        manager = NotificationManager(load_providers=False)
        event = RssFailureEvent(rss_name="Feed", rss_url="http://x", error="boom")
        with (
            patch(
                "module.notification.manager.record_event",
                new=AsyncMock(side_effect=RuntimeError("db")),
            ),
            patch("module.notification.manager.settings") as mock_settings,
        ):
            mock_settings.notification.enable = False
            await manager.send_event(event)
        await bus.drain()
        assert received == [event]

    async def test_bump_publishes_inbox_changed(self, bus):
        received: list[Event] = []
        bus.subscribe(InboxChanged.kind, received.append)
        bump_inbox_revision()
        await bus.drain()
        [event] = received
        assert isinstance(event, InboxChanged)

    def test_publish_without_bus_is_noop(self, monkeypatch):
        monkeypatch.setattr(host, "_bus", None)
        host.publish(InboxChanged(revision=1))  # 不抛错


# ---------------------------------------------------------------- message_template


class TestMessageTemplate:
    EVENT = RssFailureEvent(rss_name="Feed", rss_url="http://x", error="boom")

    async def test_default_is_describe_without_runner(self, monkeypatch):
        monkeypatch.setattr(host, "_runner", None)
        assert await render_event(self.EVENT, "telegram") == self.EVENT.describe()

    async def test_default_is_describe_without_hooks(self, runner):
        assert await render_event(self.EVENT, "telegram") == self.EVENT.describe()

    async def test_hook_rewrites_per_kind_and_channel(self, runner, registry):
        def render(message, event, channel):
            if event.kind != "rss_failure":
                return None
            return RenderedMessage(f"[{channel}] {message.title}", event.rss_name)

        registry.add_hook(points.MESSAGE_TEMPLATE, HookEntry("ext", render, 100, None))
        title, body = await render_event(self.EVENT, "bark")
        assert title == f"[bark] {self.EVENT.describe()[0]}"
        assert body == "Feed"
        other = UpdateAppliedEvent(version="1", success=True)
        assert await render_event(other, "bark") == other.describe()

    async def test_bad_return_falls_back(self, runner, registry):
        registry.add_hook(
            points.MESSAGE_TEMPLATE,
            HookEntry("ext", lambda m, e, c: "not a message", 100, None),
        )
        assert await render_event(self.EVENT, "bark") == self.EVENT.describe()

    async def test_failing_hook_falls_back_and_counts(self, runner, registry, breaker):
        def boom(message, event, channel):
            raise RuntimeError("template bug")

        registry.add_hook(points.MESSAGE_TEMPLATE, HookEntry("ext", boom, 100, None))
        assert await render_event(self.EVENT, "bark") == self.EVENT.describe()
        assert breaker._failures["ext"] == 1

    async def test_render_event_bad_return_counts_against_its_own_plugin(
        self, runner, registry, breaker
    ):
        def rewrite(message, event, channel):
            return RenderedMessage(message.title, "rewritten")

        registry.add_hook(
            points.MESSAGE_TEMPLATE,
            HookEntry("bad", lambda m, e, c: "not a message", 10, None),
        )
        registry.add_hook(
            points.MESSAGE_TEMPLATE, HookEntry("good", rewrite, 100, None)
        )
        title, body = await render_event(self.EVENT, "bark")
        assert (title, body) == (self.EVENT.describe()[0], "rewritten")
        assert breaker._failures.get("bad") == 1
        assert not breaker._failures.get("good")

    async def test_runtime_error_never_blocks_delivery(self, monkeypatch):
        bad = MagicMock()
        bad.transform = AsyncMock(side_effect=RuntimeError("undeclared point"))
        monkeypatch.setattr(host, "_runner", bad)
        assert await render_event(self.EVENT, "bark") == self.EVENT.describe()

    async def test_provider_send_event_uses_template(self, runner, registry):
        from module.notification.providers.bark import BarkProvider

        registry.add_hook(
            points.MESSAGE_TEMPLATE,
            HookEntry("ext", lambda m, e, c: RenderedMessage("T", c), 100, None),
        )
        provider_obj = BarkProvider(
            ProviderConfig(type="bark", enabled=True, device_key="k")
        )
        with patch.object(
            provider_obj, "_deliver_text", new=AsyncMock(return_value=True)
        ) as deliver:
            assert await provider_obj.send_event(self.EVENT)
        deliver.assert_awaited_once_with("T", "bark")


# ---------------------------------------------------------------- registry


def test_scoped_points_allow_same_id_in_different_plugins(registry):
    add(registry, points.MCP_TOOL, "search", object(), plugin_id="a")
    add(registry, points.MCP_TOOL, "search", object(), plugin_id="b")
    assert set(registry.providers(points.MCP_TOOL)) == {"a/search", "b/search"}
    with pytest.raises(Exception, match="已被插件"):
        add(registry, points.MCP_TOOL, "search", object(), plugin_id="a")


# ---------------------------------------------------------------- api_router


def demo_router() -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def root():
        return {"root": True}

    @router.get("/hello")
    async def hello(name: str = "world"):
        return {"hello": name}

    class Body(BaseModel):
        value: int

    @router.post("/echo")
    async def echo(body: Body):
        return {"value": body.value * 2}

    @router.get("/teapot")
    async def teapot():
        raise HTTPException(status_code=418, detail="teapot")

    @router.get("/boom")
    async def boom():
        raise RuntimeError("plugin bug")

    return router


@pytest.fixture
def routes_app(registry, breaker):
    routes = PluginRoutes(registry, breaker)
    plugins_mgr = MagicMock()
    plugins_mgr.statuses.return_value = []
    ctx = SimpleNamespace(plugin_routes=routes, plugins=plugins_mgr)
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    app.dependency_overrides[get_context] = lambda: ctx
    return app, routes


@pytest.fixture
def routes_client(routes_app):
    app, routes = routes_app

    async def user():
        return "testuser"

    app.dependency_overrides[get_current_user] = user
    return TestClient(app, raise_server_exceptions=False), routes


class TestApiRouter:
    def test_routes_follow_plugin_lifecycle(self, routes_client, registry):
        client, routes = routes_client
        assert client.get("/api/v1/plugins/demo/hello").status_code == 404

        add(registry, points.API_ROUTER, "api", demo_router(), plugin_id="demo")
        routes.sync()
        resp = client.get("/api/v1/plugins/demo/hello", params={"name": "ab"})
        assert resp.status_code == 200
        assert resp.json() == {"hello": "ab"}
        assert client.get("/api/v1/plugins/demo/").json() == {"root": True}

        registry.remove_plugin("demo")
        routes.sync()
        assert client.get("/api/v1/plugins/demo/hello").status_code == 404

    def test_body_and_errors_forwarded(self, routes_client, registry, breaker):
        client, routes = routes_client
        add(registry, points.API_ROUTER, "api", demo_router(), plugin_id="demo")
        routes.sync()
        assert client.post("/api/v1/plugins/demo/echo", json={"value": 21}).json() == {
            "value": 42
        }
        assert (
            client.post("/api/v1/plugins/demo/echo", json={"value": "x"}).status_code
            == 422
        )
        assert client.get("/api/v1/plugins/demo/teapot").status_code == 418
        assert client.get("/api/v1/plugins/demo/missing").status_code == 404
        assert breaker._failures == {}
        assert client.get("/api/v1/plugins/demo/boom").status_code == 500
        assert breaker._failures["demo"] == 1

    def test_multiple_routers_are_merged(self, routes_client, registry):
        client, routes = routes_client
        extra = APIRouter()

        @extra.get("/extra")
        async def extra_route():
            return {"extra": True}

        add(registry, points.API_ROUTER, "api", demo_router(), plugin_id="demo")
        add(registry, points.API_ROUTER, "more", extra, plugin_id="demo")
        routes.sync()
        assert client.get("/api/v1/plugins/demo/extra").json() == {"extra": True}
        assert client.get("/api/v1/plugins/demo/hello").status_code == 200

    def test_bad_factory_is_skipped(self, routes_client, registry, breaker):
        client, routes = routes_client
        add(registry, points.API_ROUTER, "api", "not a router", plugin_id="demo")
        routes.sync()
        assert routes.plugin_ids() == []
        assert breaker._failures["demo"] == 1

    def test_management_routes_not_shadowed(self, routes_client, registry):
        client, routes = routes_client
        add(registry, points.API_ROUTER, "api", demo_router(), plugin_id="settings")
        add(registry, points.API_ROUTER, "api2", demo_router(), plugin_id="providers")
        routes.sync()
        assert client.get("/api/v1/plugins").status_code == 200
        providers = client.get("/api/v1/plugins/providers")
        assert providers.status_code == 200
        assert "downloader" in providers.json()
        # PUT /plugins/{id} 仍走插件管理路由（未知插件 → 404 且 detail 来自管理路由）
        resp = client.put("/api/v1/plugins/demo", json={})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Unknown plugin: demo"
        # 插件 id 恰好是 settings/providers 时，其子路径仍可访问
        assert client.get("/api/v1/plugins/settings/hello").status_code == 200

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_auth_is_enforced(self, routes_app, registry):
        app, routes = routes_app
        add(registry, points.API_ROUTER, "api", demo_router(), plugin_id="demo")
        routes.sync()
        client = TestClient(app)
        assert client.get("/api/v1/plugins/demo/hello").status_code == 401
        assert client.get("/api/v1/plugins/unknown/x").status_code == 401


# ---------------------------------------------------------------- MCP


async def _search(args):
    return {"q": args.get("q"), "hits": [1, 2]}


class TestMcp:
    def test_plugin_tools_listed_with_namespace(self, registry):
        from module.mcp.tools import TOOLS, all_tools

        add(
            registry,
            points.MCP_TOOL,
            "search",
            McpTool("Search", _search, {"type": "object"}),
            plugin_id="demo",
        )
        names = [t.name for t in all_tools()]
        assert names[: len(TOOLS)] == [t.name for t in TOOLS]
        assert "demo__search" in names

    async def test_call_dispatches_to_plugin(self, registry):
        from module.mcp.tools import handle_tool

        add(registry, points.MCP_TOOL, "search", McpTool("S", _search), "demo")
        [content] = await handle_tool("demo__search", {"q": "x"})
        assert json.loads(content.text) == {"q": "x", "hits": [1, 2]}

    async def test_unknown_names_keep_error(self, registry):
        from module.mcp.tools import handle_tool

        add(registry, points.MCP_TOOL, "search", McpTool("S", _search), "demo")
        for name in ("nope", "demo__nope", "other__search"):
            [content] = await handle_tool(name, {})
            assert json.loads(content.text) == {"error": f"Unknown tool: {name}"}

    async def test_failure_returns_error_and_counts(self, registry, breaker):
        from module.mcp.tools import handle_tool

        async def boom(args):
            raise RuntimeError("plugin bug")

        add(registry, points.MCP_TOOL, "boom", McpTool("B", boom), "demo")
        ctx = SimpleNamespace(plugins=SimpleNamespace(breaker=breaker))
        with patch("module.mcp.plugins.get_context", return_value=ctx):
            [content] = await handle_tool("demo__boom", {})
        assert json.loads(content.text) == {"error": "plugin bug"}
        assert breaker._failures["demo"] == 1

    def test_invalid_names_and_bad_factories_skipped(self, registry):
        from module.mcp.plugins import list_plugin_tools

        add(registry, points.MCP_TOOL, "has.dot", McpTool("x", _search), "demo")
        add(registry, points.MCP_TOOL, "wrong", "not a tool", "demo")
        add(registry, points.MCP_TOOL, "ok", McpTool("x", _search), "demo")
        assert [t.name for t in list_plugin_tools()] == ["demo__ok"]

    async def test_plugin_resources(self, registry):
        from module.mcp.resources import RESOURCES, all_resources, handle_resource

        async def stats():
            return {"count": 3}

        async def text():
            return "plain"

        add(registry, points.MCP_RESOURCE, "stats", McpResource("Stats", stats), "demo")
        add(registry, points.MCP_RESOURCE, "text", McpResource("Text", text), "demo")
        uris = [str(r.uri) for r in all_resources()]
        assert uris[: len(RESOURCES)] == [str(r.uri) for r in RESOURCES]
        assert "autobangumi://plugins/demo/stats" in uris
        stats_json = await handle_resource("autobangumi://plugins/demo/stats")
        assert json.loads(stats_json) == {"count": 3}
        assert await handle_resource("autobangumi://plugins/demo/text") == "plain"
        missing = await handle_resource("autobangumi://plugins/demo/none")
        assert json.loads(missing) == {
            "error": "Unknown resource: autobangumi://plugins/demo/none"
        }

    @pytest.mark.parametrize("resource_id", ["stats", "Weekly Stats", "统计"])
    async def test_read_resource_via_protocol_returns_plugin_content(
        self, registry, resource_id
    ):
        from mcp import types

        from module.mcp import server

        async def stats():
            return {"count": 3}

        add(
            registry,
            points.MCP_RESOURCE,
            resource_id,
            McpResource("Stats", stats),
            "demo",
        )
        [listed] = [
            r
            for r in await server.list_resources()
            if str(r.uri).startswith("autobangumi://plugins/")
        ]
        handler = server.server.request_handlers[types.ReadResourceRequest]
        result = await handler(
            types.ReadResourceRequest(
                method="resources/read",
                params=types.ReadResourceRequestParams(uri=listed.uri),
            )
        )
        assert isinstance(result.root, types.ReadResourceResult)
        [content] = result.root.contents
        assert isinstance(content, types.TextResourceContents)
        assert json.loads(content.text) == {"count": 3}

    @pytest.mark.parametrize(
        "point, impl",
        [
            (points.MCP_TOOL, McpTool("bad", _search, None)),  # type: ignore[arg-type]
            (points.MCP_RESOURCE, McpResource(None, _search)),  # type: ignore[arg-type]
        ],
    )
    def test_list_malformed_plugin_spec_skipped_and_counted(
        self, registry, breaker, point, impl
    ):
        from module.mcp.resources import RESOURCES, all_resources
        from module.mcp.tools import TOOLS, all_tools

        add(registry, point, "bad", impl, "demo")
        ctx = SimpleNamespace(plugins=SimpleNamespace(breaker=breaker))
        with patch("module.mcp.plugins.get_context", return_value=ctx):
            assert len(all_tools()) == len(TOOLS)
            assert len(all_resources()) == len(RESOURCES)
        assert breaker._failures["demo"] == 1

    async def test_read_plugin_resource_hung_handler_times_out_and_counts(
        self, registry, breaker, monkeypatch
    ):
        import asyncio

        from module.mcp import plugins
        from module.mcp.resources import handle_resource

        async def hang():
            await asyncio.Event().wait()

        monkeypatch.setattr(plugins, "DEFAULT_TOOL_TIMEOUT", 0.01)
        add(registry, points.MCP_RESOURCE, "hang", McpResource("H", hang), "demo")
        ctx = SimpleNamespace(plugins=SimpleNamespace(breaker=breaker))
        with patch("module.mcp.plugins.get_context", return_value=ctx):
            raw = await handle_resource("autobangumi://plugins/demo/hang")
        assert "error" in json.loads(raw)
        assert breaker._failures["demo"] == 1

    async def test_mcp_server_handlers_include_plugins(self, registry):
        from module.mcp import server

        add(registry, points.MCP_TOOL, "search", McpTool("S", _search), "demo")
        assert "demo__search" in [t.name for t in await server.list_tools()]


# ---------------------------------------------------------------- end to end


class Options(BaseModel):
    greeting: str = "hi"


class FullPlugin(Plugin[Options]):
    """一个同时使用全部 P5 扩展点的插件。"""

    config_model = Options
    seen: list[Event] = []

    @provider(points.API_ROUTER, id="api")
    def api(self):
        router = APIRouter()

        @router.get("/greet")
        async def greet():
            return {"greeting": self.config.greeting}

        return router

    @provider(points.MCP_TOOL, id="greet")
    def greet_tool(self):
        async def handler(args):
            return {"greeting": self.config.greeting}

        return McpTool("Greet", handler)

    @subscribe("rss_failure")
    async def on_rss_failure(self, event):
        FullPlugin.seen.append(event)

    @hook(points.MESSAGE_TEMPLATE)
    def template(self, message, event, channel):
        return RenderedMessage(f"{self.config.greeting}: {message.title}", message.body)


MANIFEST = """
[plugin]
id = "full"
name = "Full"
version = "1.0.0"
sdk = ">=0.3,<1"
entry = "x:Y"
"""


async def test_plugin_end_to_end(registry, monkeypatch, tmp_path):
    from module.core import AppContext
    from module.core.scheduler import Scheduler
    from module.mcp.tools import all_tools, handle_tool

    # AppContext 会设置进程级 bus/runner；用 monkeypatch 让测试结束后复原
    monkeypatch.setattr(host, "_bus", None)
    monkeypatch.setattr(host, "_runner", None)
    candidate = PluginCandidate(
        manifest=parse_manifest(MANIFEST),
        source="builtin",
        load=lambda: FullPlugin,  # type: ignore[arg-type]
    )
    settings_obj = SimpleNamespace(
        plugins=Plugins(options={"full": {"greeting": "yo"}})
    )
    manager = PluginManager(
        settings_obj,
        registry=registry,
        discover_fn=lambda: ([candidate], []),
        data_root=tmp_path,
    )
    notifier = NotificationManager(load_providers=False)
    ctx = AppContext(
        settings_obj, notifier, Scheduler([]), MagicMock(), plugins=manager
    )
    assert host.get_bus() is manager.bus
    assert host.get_runner() is manager.runner
    FullPlugin.seen = []
    try:
        with patch("module.core.context.reset_llm_parser"):
            await manager.start()
        assert manager.statuses()[0].state == "active"

        # 事件：send_event → 总线 → 插件订阅者
        event = RssFailureEvent(rss_name="Feed", rss_url="http://x", error="boom")
        with patch("module.notification.manager.record_event", new_callable=AsyncMock):
            await notifier.send_event(event)
        await manager.bus.drain()
        assert FullPlugin.seen == [event]

        # 模板
        title, _ = await render_event(event, "bark")
        assert title == f"yo: {event.describe()[0]}"

        # MCP
        assert "full__greet" in [t.name for t in all_tools()]
        [content] = await handle_tool("full__greet", {})
        assert json.loads(content.text) == {"greeting": "yo"}

        # 路由
        app = FastAPI()
        app.include_router(v1, prefix="/api")
        app.dependency_overrides[get_context] = lambda: ctx

        async def user():
            return "u"

        app.dependency_overrides[get_current_user] = user
        client = TestClient(app)
        assert client.get("/api/v1/plugins/full/greet").json() == {"greeting": "yo"}

        # 停用后全部消失
        settings_obj.plugins.enabled["full"] = False
        await manager.apply_settings()
        assert client.get("/api/v1/plugins/full/greet").status_code == 404
        assert "full__greet" not in [t.name for t in all_tools()]
        assert await render_event(event, "bark") == event.describe()
    finally:
        await manager.stop()


# ---------------------------------------------------------------- MCP SSE


async def test_mcp_sse_endpoint_sends_response_only_once(monkeypatch):
    """/sse 结束后不能再发第二次 http.response.start（3.x 起每次断开都报
    AssertionError）。"""
    from contextlib import asynccontextmanager

    from module.mcp import server as mcp_server

    @asynccontextmanager
    async def fake_connect_sse(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        yield (object(), object())

    async def fake_run(*args, **kwargs):
        return None

    monkeypatch.setattr(mcp_server.sse, "connect_sse", fake_connect_sse)
    monkeypatch.setattr(mcp_server.server, "run", fake_run)
    sent: list[dict] = []

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    await mcp_server.handle_sse(
        {"type": "http", "method": "GET", "path": "/sse", "headers": []},
        receive,
        send,
    )
    assert [m["type"] for m in sent].count("http.response.start") == 1
