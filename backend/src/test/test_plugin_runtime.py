"""插件运行时：清单、注册表、钩子执行、事件总线、加载器与生命周期管理。"""

import asyncio
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar, cast

import pytest
from pydantic import ValidationError

from ab_sdk import Event, Plugin, PluginDisabled, Verdict, hook, provider, subscribe
from ab_sdk.events import SystemEvent
from module.models.config import Plugins
from module.plugin import ExtensionPoint, ExtensionRegistry, RegistryError
from module.plugin.bus import EventBus
from module.plugin.context import DatabaseKV, HostPluginContext
from module.plugin.loader import PluginCandidate, PluginLoadError, discover
from module.plugin.manager import PluginManager
from module.plugin.manifest import ManifestError, PluginManifest, parse_manifest
from module.plugin.registry import HookEntry, ProviderEntry
from module.plugin.runner import CircuitBreaker, HookRunner

MANIFEST = """
[plugin]
id = "{id}"
name = "Demo"
version = "1.0.0"
sdk = "{sdk}"
entry = "{entry}"
"""

UI = """
[[plugin.ui]]
slot = "bangumi.detail.tab"
element = "ab-plugin-manual-pick"
entry = "web/index.js"
title = { zh-CN = "手动选种", en-US = "Manual pick" }
"""


def write_plugin(
    root: Path,
    plugin_id: str,
    files: dict[str, str],
    *,
    entry: str = "demo:DemoPlugin",
    sdk: str = ">=0.1,<1",
) -> Path:
    plugin_dir = root / plugin_id
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.toml").write_text(
        MANIFEST.format(id=plugin_id, sdk=sdk, entry=entry)
    )
    for name, content in files.items():
        path = plugin_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content))
    return plugin_dir


def manifest(
    plugin_id: str = "demo", sdk: str = ">=0.1,<1", default_enabled: bool = True
) -> PluginManifest:
    text = MANIFEST.format(id=plugin_id, sdk=sdk, entry="x:Y")
    return parse_manifest(f"{text}default_enabled = {str(default_enabled).lower()}\n")


@dataclass(frozen=True, slots=True)
class DemoEvent(Event):
    kind: ClassVar[str] = "demo.happened"
    value: int


# ---------------------------------------------------------------- manifest


class TestManifest:
    def test_valid_manifest(self):
        m = manifest()
        assert m.id == "demo"
        assert m.entry_module == "x"
        assert m.entry_class == "Y"
        assert m.sdk_compatible("0.1.0")
        assert not m.sdk_compatible("1.0.0")

    def test_prerelease_sdk_matches_range(self):
        assert manifest(sdk=">=0.1,<1").sdk_compatible("0.2.0b1")

    @pytest.mark.parametrize(
        "text, message",
        [
            ("not toml [", "TOML"),
            ("[other]\nid = 'x'", "[plugin]"),
            (MANIFEST.format(id="Bad_ID", sdk=">=0.1", entry="a:B"), "id"),
            (MANIFEST.format(id="core", sdk=">=0.1", entry="a:B"), "保留"),
            # local 是 config/plugins/ 下本地插件的目录名
            (MANIFEST.format(id="local", sdk=">=0.1", entry="a:B"), "保留"),
            (MANIFEST.format(id="ok", sdk="garbage", entry="a:B"), "sdk"),
            (MANIFEST.format(id="ok", sdk=">=0.1", entry="no-colon"), "entry"),
        ],
    )
    def test_invalid_manifest(self, text, message):
        with pytest.raises(ManifestError, match=message):
            parse_manifest(text)

    def test_ui_entries_parsed(self):
        m = parse_manifest(
            MANIFEST.format(id="manual-pick", sdk=">=0.1", entry="a:B") + UI
        )
        [ui] = m.ui
        assert (ui.slot, ui.element, ui.entry) == (
            "bangumi.detail.tab",
            "ab-plugin-manual-pick",
            "web/index.js",
        )
        assert ui.title == {"zh-CN": "手动选种", "en-US": "Manual pick"}
        assert manifest().ui == []

    @pytest.mark.parametrize(
        "old, new, message",
        [
            ('"bangumi.detail.tab"', '"sidebar"', "slot"),
            ('"ab-plugin-manual-pick"', '"manual-pick"', "ab-plugin-"),
            ('"ab-plugin-manual-pick"', '"ab-plugin-Pick"', "ab-plugin-"),
            ('"ab-plugin-manual-pick"', '"ab-plugin-"', "ab-plugin-"),
            ('"web/index.js"', '"index.js"', "web/"),
            ('"web/index.js"', '"web/../plugin.toml"', "web/"),
            ('"web/index.js"', '"/web/index.js"', "web/"),
            ('"web/index.js"', '"web/"', "web/"),
            ('"web/index.js"', '"web\\\\index.js"', "web/"),
            ('{ zh-CN = "手动选种", en-US = "Manual pick" }', "{}", "title"),
        ],
    )
    def test_invalid_ui_entry(self, old, new, message):
        text = MANIFEST.format(id="manual-pick", sdk=">=0.1", entry="a:B") + UI.replace(
            old, new
        )
        with pytest.raises(ManifestError, match=message):
            parse_manifest(text)

    @pytest.mark.parametrize(
        "plugin_id, element, valid",
        [
            ("manual-pick", "ab-plugin-manual-pick", True),
            ("manual-pick", "ab-plugin-manual-pick-panel", True),
            # 元素名须落在本插件 id 的命名空间内，不能占用别的插件的名字
            ("other", "ab-plugin-manual-pick", False),
            ("manual", "ab-plugin-manualpick", False),
        ],
    )
    def test_ui_element_must_be_namespaced_by_plugin_id(
        self, plugin_id, element, valid
    ):
        text = MANIFEST.format(id=plugin_id, sdk=">=0.1", entry="a:B") + UI.replace(
            "ab-plugin-manual-pick", element
        )
        if valid:
            assert parse_manifest(text).ui[0].element == element
        else:
            with pytest.raises(ManifestError, match=f"ab-plugin-{plugin_id}"):
                parse_manifest(text)


# ---------------------------------------------------------------- registry


def make_registry() -> ExtensionRegistry:
    registry = ExtensionRegistry()
    registry.declare(ExtensionPoint("torrent.filter", "filter"))
    registry.declare(ExtensionPoint("strict.filter", "filter", fail_open=False))
    registry.declare(ExtensionPoint("title.transform", "transform"))
    registry.declare(ExtensionPoint("rename_strategy", "provider"))
    return registry


class TestRegistry:
    def test_redeclare_with_different_definition_fails(self):
        registry = make_registry()
        registry.declare(ExtensionPoint("torrent.filter", "filter"))  # 相同定义：幂等
        with pytest.raises(RegistryError):
            registry.declare(ExtensionPoint("torrent.filter", "transform"))

    def test_unknown_point(self):
        with pytest.raises(RegistryError, match="未知扩展点"):
            make_registry().add_hook("nope", HookEntry("p", print, 100, None))

    def test_kind_mismatch(self):
        registry = make_registry()
        with pytest.raises(RegistryError, match="@provider"):
            registry.add_hook("rename_strategy", HookEntry("p", print, 100, None))
        with pytest.raises(RegistryError, match="@hook"):
            registry.add_provider("torrent.filter", ProviderEntry("p", "x", print))

    def test_provider_id_conflict(self):
        registry = make_registry()
        registry.add_provider("rename_strategy", ProviderEntry("a", "pn", print))
        with pytest.raises(RegistryError, match="已被插件 a 占用"):
            registry.add_provider("rename_strategy", ProviderEntry("b", "pn", print))

    def test_hook_order(self):
        registry = make_registry()
        for pid, priority in (("c", 50), ("a", 100), ("b", 100)):
            registry.add_hook("torrent.filter", HookEntry(pid, print, priority, None))
        default = [e.plugin_id for e in registry.hooks("torrent.filter")]
        assert default == ["c", "a", "b"]
        explicit = [e.plugin_id for e in registry.hooks("torrent.filter", ["b"])]
        assert explicit == ["b", "c", "a"]

    def test_remove_plugin(self):
        registry = make_registry()
        registry.add_hook("torrent.filter", HookEntry("a", print, 100, None))
        registry.add_provider("rename_strategy", ProviderEntry("a", "pn", print))
        registry.remove_plugin("a")
        assert registry.hooks("torrent.filter") == []
        assert registry.providers("rename_strategy") == {}


# ---------------------------------------------------------------- runner


def runner_with(*hooks: tuple[str, str, object], threshold: int = 5):
    registry = make_registry()
    tripped: list[tuple[str, str]] = []
    breaker = CircuitBreaker(threshold, on_trip=lambda p, r: tripped.append((p, r)))
    for point, plugin_id, func in hooks:
        registry.add_hook(point, HookEntry(plugin_id, func, 100, 0.05))  # type: ignore[arg-type]
    return HookRunner(registry, breaker), tripped


class TestRunner:
    async def test_filter_short_circuits_on_reject(self):
        calls = []

        def first(x):
            calls.append("a")
            return Verdict.reject("too small")

        def second(x):
            calls.append("b")
            return True

        runner, _ = runner_with(
            ("torrent.filter", "a", first), ("torrent.filter", "b", second)
        )
        verdict = await runner.filter("torrent.filter", 1)
        assert verdict == Verdict(False, "too small")
        assert calls == ["a"]

    async def test_filter_accepts_bool_and_async(self):
        async def ok(x):
            return True

        runner, _ = runner_with(("torrent.filter", "a", ok))
        assert (await runner.filter("torrent.filter", 1)).accept

    async def test_filter_fail_open_skips_broken_hook(self):
        def boom(x):
            raise RuntimeError("bad")

        runner, _ = runner_with(("torrent.filter", "a", boom))
        assert (await runner.filter("torrent.filter", 1)).accept

    async def test_filter_fail_closed_rejects_on_error(self):
        async def slow(x):
            await asyncio.sleep(1)

        runner, _ = runner_with(("strict.filter", "a", slow))
        verdict = await runner.filter("strict.filter", 1)
        assert not verdict.accept
        assert "a" in (verdict.reason or "")

    async def test_transform_chain_and_none_keeps_value(self):
        runner, _ = runner_with(
            ("title.transform", "a", lambda v: v + "!"),
            ("title.transform", "b", lambda v: None),
            ("title.transform", "c", lambda v: v.upper()),
        )
        assert await runner.transform("title.transform", "hi") == "HI!"

    async def test_breaker_trips_after_consecutive_failures(self):
        def boom(x):
            raise RuntimeError("bad")

        runner, tripped = runner_with(("torrent.filter", "a", boom), threshold=3)
        for _ in range(5):
            await runner.filter("torrent.filter", 1)
        assert len(tripped) == 1
        assert tripped[0][0] == "a"

    async def test_success_resets_failure_count(self):
        state = {"fail": True}

        def flaky(x):
            if state["fail"]:
                raise RuntimeError("bad")
            return True

        runner, tripped = runner_with(("torrent.filter", "a", flaky), threshold=2)
        await runner.filter("torrent.filter", 1)
        state["fail"] = False
        await runner.filter("torrent.filter", 1)
        state["fail"] = True
        await runner.filter("torrent.filter", 1)
        assert tripped == []


# ---------------------------------------------------------------- bus


class TestEventBus:
    async def test_per_subscriber_order_and_isolation(self):
        bus = EventBus(handler_timeout=0.1)
        seen: list[int] = []
        errors: list[str] = []
        bus.on_error = lambda owner, reason: errors.append(owner)

        def broken(event):
            raise RuntimeError("bad")

        bus.subscribe("demo.happened", broken, owner="broken")
        bus.subscribe(
            "demo.happened",
            lambda e: seen.append(cast(DemoEvent, e).value),
            owner="ok",
        )
        for i in range(3):
            bus.publish(DemoEvent(i))
        await bus.drain()
        assert seen == [0, 1, 2]
        assert errors == ["broken"] * 3
        await bus.close()

    async def test_timeout_is_reported(self):
        bus = EventBus(handler_timeout=0.01)
        errors: list[str] = []
        bus.on_error = lambda owner, reason: errors.append(reason)

        async def slow(event):
            await asyncio.sleep(1)

        bus.subscribe("demo.happened", slow, owner="slow")
        bus.publish(DemoEvent(1))
        await bus.drain()
        assert errors and "timed out" in errors[0]
        await bus.close()

    async def test_wildcard_and_unsubscribe(self):
        bus = EventBus()
        seen: list[str] = []
        unsubscribe = bus.subscribe("*", lambda e: seen.append(e.kind))
        bus.publish(DemoEvent(1))
        await bus.drain()
        unsubscribe()
        bus.publish(DemoEvent(2))
        await bus.drain()
        assert seen == ["demo.happened"]
        await bus.close()

    async def test_close_owner_removes_only_that_owner(self):
        bus = EventBus()
        seen: list[str] = []
        bus.subscribe("demo.happened", lambda e: seen.append("a"), owner="a")
        bus.subscribe("demo.happened", lambda e: seen.append("b"), owner="b")
        await bus.close_owner("a")
        bus.publish(DemoEvent(1))
        await bus.drain()
        assert seen == ["b"]
        await bus.close()

    async def test_full_queue_drops_instead_of_blocking(self):
        bus = EventBus(queue_size=1)
        gate = asyncio.Event()
        seen: list[int] = []

        async def blocked(event):
            await gate.wait()
            seen.append(event.value)

        bus.subscribe("demo.happened", blocked)
        for i in range(5):
            bus.publish(DemoEvent(i))
        gate.set()
        await bus.drain()
        assert len(seen) < 5
        await bus.close()


# ---------------------------------------------------------------- context


class TestHostContext:
    async def test_plugin_can_only_publish_own_events(self, tmp_path):
        bus = EventBus()
        ctx = HostPluginContext("demo", None, bus, tmp_path)
        ctx.bus.publish(DemoEvent(1))
        with pytest.raises(ValueError, match="demo."):
            ctx.bus.publish(PluginDisabled(plugin_id="x", reason="fake"))
        await bus.close()

    async def test_plugin_system_event_goes_through_notification_center(
        self, tmp_path, monkeypatch
    ):
        from module.notification.manager import NotificationManager
        from module.plugin import context

        @dataclass(frozen=True, slots=True)
        class Synced(SystemEvent):
            kind: ClassVar[str] = "demo.synced"

        sent: list[Event] = []

        async def send_event(self, event):
            sent.append(event)

        monkeypatch.setattr(NotificationManager, "send_event", send_event)
        bus = EventBus()
        on_bus: list[Event] = []
        bus.subscribe("*", on_bus.append)
        ctx = HostPluginContext("demo", None, bus, tmp_path)
        ctx.bus.publish(Synced())
        await asyncio.gather(*context._notify_tasks)
        await bus.drain()
        # send_event 自己负责发布到总线，PluginBus 不再重复入队
        assert sent == [Synced()] and on_bus == []
        await bus.close()

    async def test_data_dir_created_lazily(self, tmp_path):
        ctx = HostPluginContext("demo", None, EventBus(), tmp_path)
        assert not (tmp_path / "demo").exists()
        assert ctx.data_dir.is_dir()

    async def test_kv_roundtrip_is_scoped_per_plugin(self):
        a, b = DatabaseKV("a"), DatabaseKV("b")
        assert await a.get("k", "default") == "default"
        await a.set("k", {"n": 1})
        await a.set("k", {"n": 2})
        await a.set("none", None)
        assert await a.get("k") == {"n": 2}
        assert await a.get("none", "default") is None
        assert await b.get("k") is None
        await a.delete("k")
        assert await a.get("k") is None


# ---------------------------------------------------------------- loader


DEMO_PLUGIN = """
from ab_sdk import Plugin
from .helper import VALUE


class DemoPlugin(Plugin):
    value = VALUE
"""


class TestLoader:
    def test_discover_and_load_with_relative_import(self, tmp_path):
        write_plugin(
            tmp_path / "builtin",
            "demo",
            {"demo.py": DEMO_PLUGIN, "helper.py": "VALUE = 42\n"},
        )
        candidates, errors = discover(
            builtin_root=tmp_path / "builtin",
            local_root=tmp_path / "local",
            entry_point_group="ab-test-none",
        )
        assert errors == []
        [candidate] = candidates
        assert candidate.source == "builtin" and candidate.signed
        cls = candidate.load()
        assert cls.value == 42  # type: ignore[attr-defined]
        assert "ab_plugin_demo.helper" in sys.modules
        candidate.unload()
        assert "ab_plugin_demo" not in sys.modules

    def test_builtin_wins_over_local(self, tmp_path):
        for root in ("builtin", "local"):
            write_plugin(tmp_path / root, "demo", {"demo.py": DEMO_PLUGIN})
        candidates, _ = discover(
            builtin_root=tmp_path / "builtin",
            local_root=tmp_path / "local",
            entry_point_group="ab-test-none",
        )
        assert [c.source for c in candidates] == ["builtin"]

    def test_bad_manifest_and_dir_mismatch_are_reported(self, tmp_path):
        local = tmp_path / "local"
        (local / "broken").mkdir(parents=True)
        (local / "broken" / "plugin.toml").write_text("[plugin]\nid='broken'\n")
        write_plugin(local, "demo", {"demo.py": DEMO_PLUGIN})
        (local / "demo").rename(local / "renamed")
        candidates, errors = discover(
            builtin_root=tmp_path / "none",
            local_root=local,
            entry_point_group="ab-test-none",
        )
        assert candidates == []
        assert len(errors) == 2

    def test_native_extensions_are_rejected(self, tmp_path):
        write_plugin(
            tmp_path, "demo", {"demo.py": DEMO_PLUGIN, "helper.py": "VALUE = 1\n"}
        )
        (tmp_path / "demo" / "fast.so").write_bytes(b"\0")
        candidates, _ = discover(
            builtin_root=tmp_path,
            local_root=tmp_path / "none",
            entry_point_group="ab-test-none",
        )
        with pytest.raises(PluginLoadError, match="原生扩展"):
            candidates[0].load()

    def test_vendor_dependencies_are_importable(self, tmp_path):
        write_plugin(
            tmp_path,
            "demo",
            {
                "demo.py": "from ab_sdk import Plugin\nimport ab_vendored_dep\n\n"
                "class DemoPlugin(Plugin):\n    value = ab_vendored_dep.X\n",
                "vendor/ab_vendored_dep.py": "X = 'vendored'\n",
            },
        )
        candidates, _ = discover(
            builtin_root=tmp_path,
            local_root=tmp_path / "none",
            entry_point_group="ab-test-none",
        )
        cls = candidates[0].load()
        assert cls.value == "vendored"  # type: ignore[attr-defined]
        candidates[0].unload()
        sys.modules.pop("ab_vendored_dep", None)
        assert str(tmp_path / "demo" / "vendor") not in sys.path

    @pytest.mark.parametrize(
        "source, message",
        [
            ("class DemoPlugin:\n    pass\n", "不是 ab_sdk.Plugin"),
            ("raise RuntimeError('boom')\n", "导入 demo 失败"),
            ("X = 1\n", "不存在"),
        ],
    )
    def test_invalid_entry(self, tmp_path, source, message):
        write_plugin(tmp_path, "demo", {"demo.py": source})
        candidates, _ = discover(
            builtin_root=tmp_path,
            local_root=tmp_path / "none",
            entry_point_group="ab-test-none",
        )
        with pytest.raises(PluginLoadError, match=message):
            candidates[0].load()

    def test_undecodable_manifest_is_reported(self, tmp_path):
        local = tmp_path / "local"
        (local / "demo").mkdir(parents=True)
        (local / "demo" / "plugin.toml").write_bytes(b"\xff\xfe[plugin]\n")
        candidates, errors = discover(
            builtin_root=tmp_path / "none",
            local_root=local,
            entry_point_group="ab-test-none",
        )
        assert candidates == []
        assert len(errors) == 1

    def test_entry_point_import_failure_is_reported(self, tmp_path, monkeypatch):
        import importlib.metadata

        package = tmp_path / "ab_broken_ep"
        package.mkdir()
        (package / "__init__.py").write_text("from os import ab_missing_name\n")
        monkeypatch.syspath_prepend(str(tmp_path))
        ep = importlib.metadata.EntryPoint(
            "broken", "ab_broken_ep.plugin:BrokenPlugin", "ab-test-broken"
        )
        monkeypatch.setattr(importlib.metadata, "entry_points", lambda group: [ep])
        candidates, errors = discover(
            builtin_root=tmp_path / "none",
            local_root=tmp_path / "none",
            entry_point_group="ab-test-broken",
        )
        assert candidates == []
        [error] = errors
        assert "ab_missing_name" in error.error


# ---------------------------------------------------------------- manager


class Recorder:
    def __init__(self) -> None:
        self.events: list[str] = []


def candidate_for(
    cls: type[Plugin],
    plugin_id: str = "demo",
    source: str = "builtin",
    sdk: str = ">=0.1,<1",
    default_enabled: bool = True,
) -> PluginCandidate:
    return PluginCandidate(
        manifest=manifest(plugin_id, sdk, default_enabled),
        source=source,  # type: ignore[arg-type]
        load=lambda: cls,
    )


def make_manager(*candidates: PluginCandidate, tmp_path: Path, **plugins_conf):
    settings_obj = SimpleNamespace(plugins=Plugins(**plugins_conf))
    manager = PluginManager(
        settings_obj,
        discover_fn=lambda: (list(candidates), []),
        setup_timeout=0.2,
        data_root=tmp_path,
    )
    manager.registry.declare(ExtensionPoint("torrent.filter", "filter"))
    manager.registry.declare(ExtensionPoint("rename_strategy", "provider"))
    return manager, settings_obj


def build_plugin(recorder: Recorder):
    from pydantic import BaseModel

    class Options(BaseModel):
        min_size: int = 0

    class DemoPlugin(Plugin[Options]):
        config_model = Options

        async def setup(self):
            recorder.events.append(f"setup:{self.config.min_size}")

        async def teardown(self):
            recorder.events.append("teardown")

        @hook("torrent.filter", priority=10)
        def check(self, size: int) -> Verdict:
            return Verdict(size >= self.config.min_size, "too small")

        @provider("rename_strategy", id="demo")
        def make_strategy(self):
            return "strategy"

        @subscribe("demo.happened")
        def on_demo(self, event):
            recorder.events.append(f"event:{event.value}")

    return DemoPlugin


class TestManager:
    async def test_builtin_plugin_activates_with_extensions(self, tmp_path):
        recorder = Recorder()
        manager, _ = make_manager(
            candidate_for(build_plugin(recorder)),
            tmp_path=tmp_path,
            options={"demo": {"min_size": 5}},
        )
        await manager.start()
        assert recorder.events == ["setup:5"]
        assert not (await manager.runner.filter("torrent.filter", 1)).accept
        assert (await manager.runner.filter("torrent.filter", 9)).accept
        assert manager.registry.providers("rename_strategy")["demo"].factory() == (
            "strategy"
        )
        manager.bus.publish(DemoEvent(7))
        await manager.bus.drain()
        assert recorder.events[-1] == "event:7"
        [status] = manager.statuses()
        assert status.state == "active"
        await manager.stop()
        assert recorder.events[-1] == "teardown"
        assert manager.registry.hooks("torrent.filter") == []

    async def test_unsigned_plugin_requires_opt_in(self, tmp_path):
        recorder = Recorder()
        candidate = candidate_for(build_plugin(recorder), source="local")
        manager, settings_obj = make_manager(
            candidate, tmp_path=tmp_path, enabled={"demo": True}
        )
        await manager.start()
        [status] = manager.statuses()
        assert status.state == "disabled"
        assert "allow_unsigned" in (status.error or "")
        settings_obj.plugins.allow_unsigned = True
        await manager.apply_settings()
        assert manager.statuses()[0].state == "active"
        await manager.stop()

    @pytest.mark.parametrize(
        "source, default_enabled", [("local", True), ("builtin", False)]
    )
    async def test_disabled_by_default(self, tmp_path, source, default_enabled):
        recorder = Recorder()
        manager, _ = make_manager(
            candidate_for(
                build_plugin(recorder), source=source, default_enabled=default_enabled
            ),
            tmp_path=tmp_path,
            allow_unsigned=True,
        )
        await manager.start()
        assert manager.statuses()[0].state == "disabled"
        assert recorder.events == []

    @pytest.mark.parametrize(
        "source, allow_unsigned, expect_schema",
        [("builtin", False, True), ("local", True, True), ("local", False, False)],
    )
    async def test_disabled_plugin_schema_loaded_only_if_trusted(
        self, tmp_path, source, allow_unsigned, expect_schema
    ):
        recorder = Recorder()
        manager, _ = make_manager(
            candidate_for(build_plugin(recorder), source=source, default_enabled=False),
            tmp_path=tmp_path,
            allow_unsigned=allow_unsigned,
        )
        await manager.start()
        [status] = manager.statuses()
        assert status.state == "disabled"
        # 只导入代码取 schema：不 setup、不注册扩展
        assert recorder.events == []
        assert (status.config_schema is not None) == expect_schema
        if expect_schema:
            assert "min_size" in status.config_schema["properties"]  # type: ignore[index]
            manager.validate_options("demo", {"min_size": 3})
            with pytest.raises(ValidationError):
                manager.validate_options("demo", {"min_size": "x"})

    @pytest.mark.parametrize("first_probe_fails", [False, True])
    async def test_disabled_plugin_schema_refreshed_on_reload(
        self, tmp_path, first_probe_fails
    ):
        from pydantic import BaseModel

        class NewOptions(BaseModel):
            level: int = 1

        def broken():
            raise RuntimeError("boom")

        old = build_plugin(Recorder())
        candidates = [candidate_for(old, default_enabled=False)]
        if first_probe_fails:
            candidates[0].load = broken  # type: ignore[method-assign]
        manager, _ = make_manager(*candidates, tmp_path=tmp_path)
        await manager.start()
        assert (manager.statuses()[0].config_schema is None) == first_probe_fails

        # 升级插件目录后重新发现：换成 config_model 不同的新类
        new = type("NewPlugin", (Plugin,), {"config_model": NewOptions})
        manager._discover = lambda: ([candidate_for(new, default_enabled=False)], [])
        await manager.apply_settings()
        [status] = manager.statuses()
        assert list(status.config_schema["properties"]) == ["level"]  # type: ignore[index]

    @pytest.mark.parametrize(
        "conf, sdk, message",
        [
            ({"options": {"demo": {"min_size": "nope"}}}, ">=0.1,<1", "min_size"),
            ({}, ">=9", "需要 ab_sdk"),
        ],
    )
    async def test_load_errors_are_reported(self, tmp_path, conf, sdk, message):
        recorder = Recorder()
        manager, _ = make_manager(
            candidate_for(build_plugin(recorder), sdk=sdk), tmp_path=tmp_path, **conf
        )
        seen: list[Event] = []
        manager.bus.subscribe(PluginDisabled.kind, seen.append)
        await manager.start()
        [status] = manager.statuses()
        assert status.state == "error"
        assert message in (status.error or "")
        await manager.bus.drain()
        assert len(seen) == 1
        await manager.stop()

    async def test_subscribe_timeout_overrides_bus_default(self, tmp_path):
        seen: list[int] = []

        class Slow(Plugin):
            @subscribe("demo.happened", timeout=5)
            async def on_demo(self, event):
                await asyncio.sleep(0.05)
                seen.append(event.value)

        manager, _ = make_manager(candidate_for(Slow), tmp_path=tmp_path)
        errors: list[str] = []
        manager.bus = EventBus(
            handler_timeout=0.01, on_error=lambda owner, reason: errors.append(reason)
        )
        await manager.start()
        manager.bus.publish(DemoEvent(1))
        await manager.bus.drain()
        assert (seen, errors) == ([1], [])
        await manager.stop()

    async def test_failed_setup_rolls_back_registrations(self, tmp_path):
        recorder = Recorder()

        class Broken(Plugin):
            @hook("torrent.filter")
            def check(self, x):
                return True

            async def setup(self):
                recorder.events.append("setup")
                raise RuntimeError("cannot connect")

            async def teardown(self):
                recorder.events.append("teardown")

        manager, _ = make_manager(candidate_for(Broken), tmp_path=tmp_path)
        await manager.start()
        assert manager.registry.hooks("torrent.filter") == []
        assert manager.statuses()[0].error == "cannot connect"
        # setup 中途创建的资源由 teardown 释放
        assert recorder.events == ["setup", "teardown"]

    async def test_disabling_failed_plugin_shows_disabled(self, tmp_path):
        class Broken(Plugin):
            async def setup(self):
                raise RuntimeError("cannot connect")

        manager, settings_obj = make_manager(candidate_for(Broken), tmp_path=tmp_path)
        await manager.start()
        settings_obj.plugins.enabled = {"demo": False}
        await manager.apply_settings()
        [status] = manager.statuses()
        assert (status.state, status.error) == ("disabled", "未启用")

    async def test_unknown_extension_point_fails_load(self, tmp_path):
        recorder = Recorder()

        class Typo(Plugin):
            @hook("torrent.filtr")
            def check(self, x):
                return True

            async def teardown(self):
                recorder.events.append("teardown")

        manager, _ = make_manager(candidate_for(Typo), tmp_path=tmp_path)
        await manager.start()
        assert "未知扩展点" in (manager.statuses()[0].error or "")
        # setup 未执行，没有需要释放的资源
        assert recorder.events == []

    async def test_apply_settings_reloads_on_option_change_only(self, tmp_path):
        recorder = Recorder()
        manager, settings_obj = make_manager(
            candidate_for(build_plugin(recorder)), tmp_path=tmp_path
        )
        await manager.start()
        await manager.apply_settings()
        assert recorder.events == ["setup:0"]
        settings_obj.plugins.options = {"demo": {"min_size": 3}}
        await manager.apply_settings()
        assert recorder.events == ["setup:0", "teardown", "setup:3"]
        settings_obj.plugins.enabled = {"demo": False}
        await manager.apply_settings()
        assert recorder.events[-1] == "teardown"
        assert manager.statuses()[0].state == "disabled"
        await manager.stop()

    async def test_failed_plugin_retried_only_after_its_config_changes(self, tmp_path):
        attempts = []

        class Flaky(Plugin):
            async def setup(self):
                attempts.append(1)
                raise RuntimeError("bad")

        manager, settings_obj = make_manager(candidate_for(Flaky), tmp_path=tmp_path)
        await manager.start()
        await manager.apply_settings()
        assert len(attempts) == 1
        settings_obj.plugins.options = {"demo": {"retry": True}}
        await manager.apply_settings()
        assert len(attempts) == 2

    async def test_breaker_trip_disables_plugin(self, tmp_path):
        class Crashy(Plugin):
            @hook("torrent.filter")
            def check(self, x):
                raise RuntimeError("bad")

        manager, _ = make_manager(candidate_for(Crashy), tmp_path=tmp_path)
        seen: list[Event] = []
        manager.bus.subscribe(PluginDisabled.kind, seen.append)
        await manager.start()
        for _ in range(5):
            await manager.runner.filter("torrent.filter", 1)
        await asyncio.gather(*manager._pending)
        await manager.bus.drain()
        [status] = manager.statuses()
        assert status.state == "error"
        assert "连续失败" in (status.error or "")
        assert manager.registry.hooks("torrent.filter") == []
        assert len(seen) == 1
        await manager.stop()

    async def test_subscriber_success_resets_failure_count(self, tmp_path):
        class Sometimes(Plugin):
            @subscribe("demo.happened")
            def on_demo(self, event):
                if event.value < 0:
                    raise RuntimeError("transient")

        manager, _ = make_manager(candidate_for(Sometimes), tmp_path=tmp_path)
        await manager.start()
        for value in [-1] * 4 + [1] + [-1] * 4:
            manager.bus.publish(DemoEvent(value))
        await manager.bus.drain()
        await asyncio.gather(*manager._pending)
        assert manager.statuses()[0].state == "active"
        await manager.stop()

    async def test_stale_breaker_trip_spares_reloaded_instance(self, tmp_path):
        recorder = Recorder()
        manager, _ = make_manager(
            candidate_for(build_plugin(recorder)), tmp_path=tmp_path
        )
        await manager.start()
        # 熔断任务尚未拿到锁时，插件已被重新加载（安装升级 / dev_mode）
        manager._on_trip("demo", "连续失败 5 次")
        await manager.reload("demo")
        await asyncio.gather(*manager._pending)
        [status] = manager.statuses()
        assert status.state == "active"
        assert recorder.events == ["setup:0", "teardown", "setup:0"]
        await manager.stop()

    async def test_end_to_end_from_directory(self, tmp_path):
        write_plugin(
            tmp_path / "builtin",
            "demo",
            {"demo.py": """
                from ab_sdk import Plugin, hook

                class DemoPlugin(Plugin):
                    @hook("torrent.filter")
                    def check(self, size):
                        return size > 1
                """},
        )
        settings_obj = SimpleNamespace(plugins=Plugins())
        manager = PluginManager(
            settings_obj,
            discover_fn=lambda: discover(
                builtin_root=tmp_path / "builtin",
                local_root=tmp_path / "local",
                entry_point_group="ab-test-none",
            ),
            data_root=tmp_path / "data",
        )
        manager.registry.declare(ExtensionPoint("torrent.filter", "filter"))
        await manager.start()
        assert not (await manager.runner.filter("torrent.filter", 1)).accept
        await manager.stop()
        assert "ab_plugin_demo" not in sys.modules


# ---------------------------------------------------------------- API


class TestPluginsApi:
    def test_list_plugins(self, app, authed_client, monkeypatch):
        from module.api.deps import get_context
        from module.conf import settings
        from module.plugin.manager import PluginStatus

        status = PluginStatus(
            id="demo",
            name="Demo",
            version="1.0.0",
            source="local",
            signed=False,
            state="disabled",
            error="未签名插件需要开启 plugins.allow_unsigned",
        )
        ctx = SimpleNamespace(plugins=SimpleNamespace(statuses=lambda: [status]))
        monkeypatch.setattr(settings, "plugins", Plugins())
        app.dependency_overrides[get_context] = lambda: ctx
        response = authed_client.get("/api/v1/plugins")
        assert response.status_code == 200
        [item] = response.json()["plugins"]
        assert item["id"] == "demo"
        assert item["state"] == "disabled"
        assert item["signed"] is False
        assert item["permissions"] == []

    def test_list_plugins_requires_auth(self, unauthed_client):
        assert unauthed_client.get("/api/v1/plugins").status_code == 401
