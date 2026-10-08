"""P2 扩展点：下载器、通知渠道、LLM、搜索站点、定时任务与插件管理 API。"""

import asyncio
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from ab_sdk import points, secret_field
from ab_sdk.downloader import (
    AddResult,
    DownloaderCapabilities,
    DownloaderConnection,
)
from ab_sdk.llm import LLMProviderAdapter, ProviderInfo
from ab_sdk.notify import NotificationMessage, NotifierSettings
from ab_sdk.search import SearchSite
from ab_sdk.tasks import ScheduledTask
from module.conf import settings
from module.core.plugin_tasks import PluginTasks
from module.core.scheduler import Scheduler
from module.models.bangumi import Notification
from module.models.config import NotificationProvider as ProviderConfig
from module.models.config import Plugins
from module.plugin import host
from module.plugin.registry import ProviderEntry
from module.plugin.runner import CircuitBreaker
from module.plugin.secrets import MASK, mask_options, restore_options


@pytest.fixture
def registry(monkeypatch):
    """每个测试一个全新的进程级注册表（含 core 登记）。"""
    monkeypatch.setattr(host, "_registry", None)
    return host.get_registry()


def add_plugin_provider(registry, point, provider_id, impl, plugin_id="ext"):
    registry.add_provider(point, ProviderEntry(plugin_id, provider_id, lambda: impl))


# ---------------------------------------------------------------- core


def test_core_providers_registered(registry):
    downloaders = registry.providers(points.DOWNLOADER)
    assert set(downloaders) == {"qbittorrent", "aria2", "mock"}
    assert all(e.plugin_id == host.CORE for e in downloaders.values())
    assert {"telegram", "bark", "webhook"} <= set(registry.providers(points.NOTIFIER))
    assert host.plugin_provider_ids(points.DOWNLOADER) == []


# ---------------------------------------------------------------- downloader


class FakeDownloader:
    capabilities: ClassVar = DownloaderCapabilities(False, False, False, False)

    def __init__(self, conn: DownloaderConnection) -> None:
        self.conn = conn

    async def auth(self, retry: int = 3) -> bool:
        return True

    async def logout(self) -> None:
        return None

    async def add_torrents(self, *args, **kwargs) -> AddResult:
        return AddResult.ADDED


class TestDownloader:
    def test_plugin_downloader_is_used_by_facade(self, registry, monkeypatch):
        from module.downloader import DownloadClient

        add_plugin_provider(registry, points.DOWNLOADER, "fake", FakeDownloader)
        monkeypatch.setattr(settings.downloader, "type", "fake")
        monkeypatch.setattr(settings.downloader, "host_", "example:1234")
        client = DownloadClient()
        assert isinstance(client.client, FakeDownloader)
        assert client.client.conn.host == "example:1234"
        assert host.plugin_provider_ids(points.DOWNLOADER) == ["fake"]

    def test_unknown_type_raises(self, registry, monkeypatch):
        from module.downloader import DownloadClient

        monkeypatch.setattr(settings.downloader, "type", "nope")
        with pytest.raises(Exception, match="Unsupported downloader type"):
            DownloadClient()


# ---------------------------------------------------------------- notifier


class RecordingNotifier:
    def __init__(self, conf: NotifierSettings) -> None:
        self.conf = conf
        self.sent: list[NotificationMessage] = []

    async def send(self, message: NotificationMessage) -> bool:
        self.sent.append(message)
        return True

    async def test(self) -> tuple[bool, str]:
        return True, f"ok:{self.conf.extra.get('room')}"


class TestNotifier:
    async def test_plugin_notifier_receives_rendered_messages(self, registry):
        from module.notification.resolve import PluginNotifier, build_provider

        created: list[RecordingNotifier] = []

        def factory(conf: NotifierSettings) -> RecordingNotifier:
            created.append(RecordingNotifier(conf))
            return created[-1]

        add_plugin_provider(registry, points.NOTIFIER, "chat", factory)
        cfg = ProviderConfig.model_validate(
            {"type": "chat", "template": "{{title}} E{{episode}}", "room": "42"}
        )
        provider = build_provider(cfg)
        assert isinstance(provider, PluginNotifier)
        [notifier] = created
        assert notifier.conf.extra == {"room": "42"}

        async with provider:
            await provider.send(
                Notification(official_title="Show", season=1, episode=3)
            )
            await provider._deliver_text("RSS 失败", "detail")
            assert await provider.test() == (True, "ok:42")
        episode, event = notifier.sent
        assert episode.kind == "episode" and episode.body == "Show E3"
        assert episode.episode == 3 and episode.poster_url is None
        assert (event.kind, event.title, event.body) == ("event", "RSS 失败", "detail")

    def test_core_provider_still_built_from_class(self, registry):
        from module.notification.providers import TelegramProvider
        from module.notification.resolve import build_provider

        provider = build_provider(ProviderConfig(type="telegram", token="t"))
        assert isinstance(provider, TelegramProvider)

    def test_manager_skips_unknown_and_loads_plugin(self, registry, monkeypatch):
        from module.notification import NotificationManager

        add_plugin_provider(registry, points.NOTIFIER, "chat", RecordingNotifier)
        monkeypatch.setattr(
            settings.notification,
            "providers",
            [ProviderConfig(type="chat"), ProviderConfig(type="missing")],
        )
        assert len(NotificationManager()) == 1

    def test_build_provider_mixed_case_plugin_id_resolves(self, registry):
        from module.notification.resolve import PluginNotifier, build_provider

        add_plugin_provider(registry, points.NOTIFIER, "MyChannel", RecordingNotifier)
        provider = build_provider(ProviderConfig(type="MyChannel"))
        assert isinstance(provider, PluginNotifier)

    def test_extra_fields_survive_config_roundtrip(self):
        cfg = ProviderConfig.model_validate({"type": "chat", "room": "42"})
        assert cfg.model_dump(by_alias=True)["room"] == "42"


# ---------------------------------------------------------------- LLM


def broken_factory():
    raise RuntimeError("factory broken")


def make_adapter(adapter_id: str):
    class Adapter(LLMProviderAdapter):
        info = ProviderInfo(id=adapter_id, display_name="Ext LLM")

        async def parse(self, raw: str) -> dict | None:
            return None

        async def list_models(self) -> list[str]:
            return []

    return Adapter


class TestLLMProvider:
    def test_plugin_adapter_listed_and_resolvable(self, registry):
        from module.parser.analyser.providers.registry import ProviderRegistry

        adapter = make_adapter("ext-llm")
        add_plugin_provider(registry, points.LLM_PROVIDER, "ext-llm", adapter)
        llm_registry = ProviderRegistry()
        assert llm_registry.resolve("ext-llm") is adapter
        info = next(i for i in llm_registry.list_infos() if i.id == "ext-llm")
        assert info.builtin is False

    def test_mismatched_id_is_skipped(self, registry):
        from module.parser.analyser.providers.registry import ProviderRegistry

        add_plugin_provider(
            registry, points.LLM_PROVIDER, "claimed", make_adapter("other")
        )
        with pytest.raises(ValueError):
            ProviderRegistry().resolve("claimed")

    def test_provider_registry_broken_factory_skipped(self, registry):
        from module.parser.analyser.providers.registry import ProviderRegistry

        add_plugin_provider(
            registry, points.LLM_PROVIDER, "ext-llm", make_adapter("ext-llm")
        )
        registry.add_provider(
            points.LLM_PROVIDER, ProviderEntry("bad", "bad-llm", broken_factory)
        )
        llm_registry = ProviderRegistry()
        assert "ext-llm" in {i.id for i in llm_registry.list_infos()}
        assert llm_registry.resolve("ext-llm").info.id == "ext-llm"

    def test_builtin_cannot_be_shadowed(self, registry):
        from module.parser.analyser.providers.builtin import BUILTIN
        from module.parser.analyser.providers.registry import ProviderRegistry

        add_plugin_provider(
            registry, points.LLM_PROVIDER, "openai", make_adapter("openai")
        )
        assert ProviderRegistry().resolve("openai") is BUILTIN["openai"]


# ---------------------------------------------------------------- search


class TestSearchSite:
    def test_plugin_site_merged_and_user_config_wins(self, registry):
        from module.searcher import available_sites
        from module.searcher.provider import search_url

        add_plugin_provider(
            registry, points.SEARCH_SITE, "acg", SearchSite("https://acg/?q=%s")
        )
        add_plugin_provider(
            registry, points.SEARCH_SITE, "mikan", SearchSite("https://evil/%s")
        )
        user = {"mikan": {"url": "https://mikanani.me/?q=%s", "parser": "mikan"}}
        with patch("module.searcher.provider.get_provider", return_value=user):
            sites = available_sites()
            item = search_url("acg", ["Frieren", "S2"])
        assert sites["mikan"]["url"] == "https://mikanani.me/?q=%s"
        assert sites["acg"] == {"url": "https://acg/?q=%s", "parser": "tmdb"}
        assert item.url == "https://acg/?q=Frieren+S2"
        assert item.parser == "tmdb"

    def test_available_sites_broken_factory_skipped(self, registry):
        from module.searcher import available_sites

        add_plugin_provider(
            registry, points.SEARCH_SITE, "acg", SearchSite("https://acg/?q=%s")
        )
        registry.add_provider(
            points.SEARCH_SITE, ProviderEntry("bad", "bad-site", broken_factory)
        )
        with patch("module.searcher.provider.get_provider", return_value={}):
            sites = available_sites()
        assert set(sites) == {"acg"}


# ---------------------------------------------------------------- tasks


class TestPluginTasks:
    def make(self, registry, threshold=5):
        scheduler = Scheduler([])
        tripped: list[str] = []
        breaker = CircuitBreaker(threshold, on_trip=lambda p, r: tripped.append(p))
        return scheduler, PluginTasks(scheduler, registry, breaker), tripped

    async def test_task_added_started_and_removed(self, registry):
        scheduler, bridge, _ = self.make(registry)
        ran = asyncio.Event()

        async def run():
            ran.set()

        entry = ProviderEntry("ext", "sync", lambda: ScheduledTask(run, 3600))
        registry.add_provider(points.SCHEDULED_TASK, entry)
        scheduler.start_all()
        await bridge.sync()
        [task] = scheduler.tasks
        assert task.name == "plugin:ext:sync" and task.running
        await asyncio.wait_for(ran.wait(), 1)

        registry.remove_plugin("ext")
        await bridge.sync()
        assert scheduler.tasks == [] and not task.running
        await scheduler.stop_all()

    async def test_reloaded_plugin_replaces_task(self, registry):
        scheduler, bridge, _ = self.make(registry)
        spec = ScheduledTask(AsyncMock(), 60)
        registry.add_provider(
            points.SCHEDULED_TASK, ProviderEntry("ext", "sync", lambda: spec)
        )
        await bridge.sync()
        [first] = scheduler.tasks
        registry.remove_plugin("ext")
        registry.add_provider(
            points.SCHEDULED_TASK, ProviderEntry("ext", "sync", lambda: spec)
        )
        await bridge.sync()
        [second] = scheduler.tasks
        assert first is not second

    async def test_failures_count_toward_breaker(self, registry):
        scheduler, bridge, tripped = self.make(registry, threshold=2)

        async def boom():
            raise RuntimeError("bad")

        registry.add_provider(
            points.SCHEDULED_TASK,
            ProviderEntry("ext", "sync", lambda: ScheduledTask(boom, 0.01)),
        )
        await bridge.sync()
        scheduler.start_all()
        for _ in range(100):
            if tripped:
                break
            await asyncio.sleep(0.02)
        await scheduler.stop_all()
        assert tripped == ["ext"]

    async def test_factory_failure_is_skipped(self, registry):
        scheduler, bridge, _ = self.make(registry, threshold=1)

        def broken():
            raise RuntimeError("no")

        registry.add_provider(
            points.SCHEDULED_TASK, ProviderEntry("ext", "sync", broken)
        )
        await bridge.sync()
        assert scheduler.tasks == []

    @pytest.mark.parametrize("bad_spec", [None, object()])
    async def test_sync_malformed_spec_skipped_and_recorded(self, registry, bad_spec):
        scheduler, bridge, tripped = self.make(registry, threshold=1)
        registry.add_provider(
            points.SCHEDULED_TASK, ProviderEntry("bad", "a", lambda: bad_spec)
        )
        registry.add_provider(
            points.SCHEDULED_TASK,
            ProviderEntry("ext", "b", lambda: ScheduledTask(AsyncMock(), 60)),
        )
        await bridge.sync()
        assert [t.name for t in scheduler.tasks] == ["plugin:ext:b"]
        assert tripped == ["bad"]

    async def test_enabled_flip_skips_run(self, registry):
        scheduler, bridge, _ = self.make(registry)
        state = {"on": True}
        run = AsyncMock()
        registry.add_provider(
            points.SCHEDULED_TASK,
            ProviderEntry(
                "ext",
                "sync",
                lambda: ScheduledTask(run, 0.01, enabled=lambda: state["on"]),
            ),
        )
        await bridge.sync()
        scheduler.start_all()
        for _ in range(50):
            if run.await_count:
                break
            await asyncio.sleep(0.02)
        state["on"] = False
        await asyncio.sleep(0.05)
        count = run.await_count
        await asyncio.sleep(0.1)
        await scheduler.stop_all()
        assert count >= 1 and run.await_count == count

    async def test_enabled_raising_counts_toward_breaker(self, registry):
        scheduler, bridge, tripped = self.make(registry, threshold=2)

        def enabled() -> bool:
            raise RuntimeError("bad")

        registry.add_provider(
            points.SCHEDULED_TASK,
            ProviderEntry(
                "ext", "sync", lambda: ScheduledTask(AsyncMock(), 0.01, enabled=enabled)
            ),
        )
        await bridge.sync()
        scheduler.start_all()
        for _ in range(100):
            if tripped:
                break
            await asyncio.sleep(0.02)
        await scheduler.stop_all()
        assert tripped == ["ext"]


# ---------------------------------------------------------------- secrets


class SecretOptions(BaseModel):
    site: str = ""
    cookie: str = secret_field(description="站点 Cookie")


SCHEMA = SecretOptions.model_json_schema()


class TestSecrets:
    def test_mask_and_restore(self):
        masked = mask_options({"site": "a", "cookie": "c=1"}, SCHEMA)
        assert masked == {"site": "a", "cookie": MASK}
        restored = restore_options(dict(masked), {"cookie": "c=1"}, SCHEMA)
        assert restored == {"site": "a", "cookie": "c=1"}
        assert restore_options({"cookie": MASK}, {}, SCHEMA) == {}
        assert mask_options({"cookie": ""}, SCHEMA) == {"cookie": ""}

    def test_mask_options_without_schema_masks_all(self):
        masked = mask_options({"site": "a", "cookie": "c=1", "n": 3}, None)
        assert masked == {"site": MASK, "cookie": MASK, "n": 3}
        current = {"site": "a", "cookie": "c=1"}
        restored = restore_options(dict(masked), current, None)
        assert restored == {"site": "a", "cookie": "c=1", "n": 3}


# ---------------------------------------------------------------- API


@pytest.fixture
def plugin_ctx(app, monkeypatch):
    from module.api.deps import get_context
    from module.plugin.manager import PluginStatus

    monkeypatch.setattr(settings, "plugins", Plugins())
    status = PluginStatus(
        id="demo",
        name="Demo",
        version="1.0.0",
        source="local",
        signed=False,
        state="active",
        enabled=True,
        config_schema=SCHEMA,
    )
    manager = MagicMock()
    manager.statuses.return_value = [status]
    manager.validate_options.side_effect = lambda _pid, opts: (
        SecretOptions.model_validate(opts)
    )
    ctx = SimpleNamespace(plugins=manager)
    app.dependency_overrides[get_context] = lambda: ctx
    save = AsyncMock()
    monkeypatch.setattr("module.api.plugins._save_and_apply", save)
    return ctx, save


class TestPluginsApi:
    def test_overview_masks_secret_options(self, authed_client, plugin_ctx):
        settings.plugins.options["demo"] = {"site": "a", "cookie": "c=1"}
        data = authed_client.get("/api/v1/plugins").json()
        assert data["allow_unsigned"] is False
        [plugin] = data["plugins"]
        assert plugin["options"] == {"site": "a", "cookie": MASK}
        assert plugin["config_schema"]["properties"]["cookie"]["secret"] is True

    def test_update_restores_mask_and_saves(self, authed_client, plugin_ctx):
        _, save = plugin_ctx
        settings.plugins.options["demo"] = {"site": "a", "cookie": "c=1"}
        response = authed_client.put(
            "/api/v1/plugins/demo",
            json={"enabled": False, "options": {"site": "b", "cookie": MASK}},
        )
        assert response.status_code == 200
        assert settings.plugins.options["demo"] == {"site": "b", "cookie": "c=1"}
        assert settings.plugins.enabled["demo"] is False
        save.assert_awaited_once()

    def test_update_rejects_invalid_options(self, authed_client, plugin_ctx):
        _, save = plugin_ctx
        response = authed_client.put(
            "/api/v1/plugins/demo", json={"options": {"site": ["not", "str"]}}
        )
        assert response.status_code == 422
        save.assert_not_awaited()
        assert "demo" not in settings.plugins.options

    def test_update_unknown_plugin(self, authed_client, plugin_ctx):
        assert authed_client.put("/api/v1/plugins/x", json={}).status_code == 404

    def test_allow_unsigned(self, authed_client, plugin_ctx):
        response = authed_client.put(
            "/api/v1/plugins/settings", json={"allow_unsigned": True}
        )
        assert response.json()["allow_unsigned"] is True
        assert settings.plugins.allow_unsigned is True

    def test_providers(self, authed_client, plugin_ctx, registry):
        add_plugin_provider(registry, points.DOWNLOADER, "fake", FakeDownloader)
        data = authed_client.get("/api/v1/plugins/providers").json()
        assert data == {
            "downloader": ["fake"],
            "notifier": [],
            "search_site": [],
            "metadata_provider": [],
        }

    def test_config_get_masks_plugin_secrets(self, authed_client, plugin_ctx):
        settings.plugins.options["demo"] = {"site": "a", "cookie": "c=1"}
        data = authed_client.get("/api/v1/config/get").json()
        assert data["plugins"]["options"]["demo"] == {"site": "a", "cookie": MASK}


# ---------------------------------------------------------------- regressions


class TestPluginChangeRebuildsState:
    async def test_on_change_rebuilds_notifier_and_syncs_tasks(self, registry):
        from module.core import AppContext

        ctx = AppContext.build(settings)
        ctx.notifier = MagicMock()
        with patch("module.core.context.reset_llm_parser") as reset_llm:
            await ctx.plugins.on_change()  # type: ignore[misc]
        ctx.notifier.rebuild.assert_called_once()
        reset_llm.assert_called_once()

    def test_reloaded_plugin_downloader_retires_cached_client(
        self, registry, monkeypatch
    ):
        from module.downloader import DownloadClient

        add_plugin_provider(registry, points.DOWNLOADER, "fake", FakeDownloader)
        monkeypatch.setattr(settings.downloader, "type", "fake")
        first = DownloadClient().client
        assert DownloadClient().client is first
        # 插件重载：同 id 的新登记项
        registry.remove_plugin("ext")
        add_plugin_provider(registry, points.DOWNLOADER, "fake", FakeDownloader)
        assert DownloadClient().client is not first
