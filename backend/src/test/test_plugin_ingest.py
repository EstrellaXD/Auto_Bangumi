"""P3 ingest 扩展点：torrent.filter、title.parsed、torrent.adding、
http.request、metadata_provider，以及内置插件 ingest-filters。"""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from ab_sdk import Verdict, points
from ab_sdk.ingest import (
    AddRequest,
    BangumiInfo,
    HttpRequest,
    Metadata,
    MetadataRequest,
    TorrentInfo,
)
from ab_sdk.testing import create_plugin
from module.conf import settings
from module.database import Database
from module.downloader import AddResult
from module.models import Bangumi, Torrent
from module.models.config import LLM, Plugins
from module.parser import TitleParser
from module.parser.analyser.tokenizer import ParsedRelease
from module.plugin import PluginManager, host
from module.plugin.loader import BUILTIN_ROOT, discover
from module.plugin.registry import HookEntry, ProviderEntry
from module.plugin.runner import CircuitBreaker, HookRunner
from module.rss.analyser import RSSAnalyser
from module.rss.engine import RSSEngine
from test.factories import make_bangumi, make_rss_item, make_torrent

TORRENT_NAME = "[Sub] Mushoku Tensei - 12 [1080p].mkv"


@pytest.fixture
def plugins(monkeypatch):
    """全新的进程级注册表 + 已设置的 runner（模拟 AppContext 构建后的状态）。"""
    monkeypatch.setattr(host, "_registry", None)
    registry = host.get_registry()
    tripped: list[str] = []
    breaker = CircuitBreaker(3, on_trip=lambda plugin_id, _: tripped.append(plugin_id))
    runner = HookRunner(registry, breaker, default_timeout=1.0)
    monkeypatch.setattr(host, "_runner", runner)
    return SimpleNamespace(registry=registry, runner=runner, tripped=tripped)


@pytest.fixture
def no_runner(monkeypatch):
    monkeypatch.setattr(host, "_registry", None)
    monkeypatch.setattr(host, "_runner", None)
    return host.get_registry()


def add_hook(registry, point, func, plugin_id="ext", priority=100):
    registry.add_hook(point, HookEntry(plugin_id, func, priority, None))


@pytest_asyncio.fixture
async def rss_engine(db_engine):
    return RSSEngine(Database(engine=db_engine))


async def refresh_with(engine: RSSEngine, torrents: list[Torrent]):
    client = AsyncMock()
    client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
    with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as get:
        get.return_value = torrents
        await engine.refresh_rss(client)
    return client


async def seed(engine: RSSEngine, **bangumi_overrides) -> None:
    await engine.db.rss.add(make_rss_item(enabled=True))
    defaults = {"title_raw": "Mushoku Tensei", "filter": ""}
    await engine.db.bangumi.add(make_bangumi(**{**defaults, **bangumi_overrides}))


# ---------------------------------------------------------------- host


class TestHost:
    def test_points_declared(self, plugins):
        reg = plugins.registry
        assert reg.point(points.TORRENT_FILTER).kind == "filter"
        assert reg.point(points.TORRENT_FILTER).fail_open is True
        for name in (points.TITLE_PARSED, points.TORRENT_ADDING, points.HTTP_REQUEST):
            assert reg.point(name).kind == "transform"
        providers = reg.providers(points.METADATA_PROVIDER)
        assert set(providers) == {"mikan", "tmdb"}
        assert all(e.plugin_id == host.CORE for e in providers.values())

    def test_hook_runner_fast_path(self, plugins, no_runner):
        # no_runner 覆盖了 plugins 设置的 runner
        assert host.hook_runner(points.TORRENT_FILTER) is None

    def test_hook_runner_requires_hooks(self, plugins):
        assert host.hook_runner(points.TORRENT_FILTER) is None
        add_hook(plugins.registry, points.TORRENT_FILTER, lambda *a: True)
        assert host.hook_runner(points.TORRENT_FILTER) is plugins.runner

    async def test_transform_expect_rejects_wrong_type(self, plugins):
        add_hook(plugins.registry, points.TITLE_PARSED, lambda r: "oops", "bad")
        add_hook(
            plugins.registry,
            points.TITLE_PARSED,
            lambda r: replace(r, group="G"),
            "good",
            priority=200,
        )
        release = ParsedRelease(raw="x", title_en="X")
        result = await plugins.runner.transform(
            points.TITLE_PARSED, release, expect=ParsedRelease
        )
        assert result == replace(release, group="G")

    def test_app_context_sets_runner(self, monkeypatch):
        from module.core.context import AppContext

        monkeypatch.setattr(host, "_runner", None)
        ctx = AppContext.build(settings)
        assert host.get_runner() is ctx.plugins.runner


# ---------------------------------------------------------------- torrent.filter


class TestTorrentFilter:
    async def test_reject_skips_download_and_unlinks(self, rss_engine, plugins):
        await seed(rss_engine)
        seen = []

        def reject(torrent, release, bangumi):
            seen.append((torrent, release, bangumi))
            return Verdict.reject("no")

        add_hook(plugins.registry, points.TORRENT_FILTER, reject)
        client = await refresh_with(
            rss_engine, [Torrent(name=TORRENT_NAME, url="https://e/1.torrent")]
        )

        client.add_torrent.assert_not_called()
        stored = await rss_engine.db.torrent.search_all()
        assert len(stored) == 1
        assert stored[0].bangumi_id is None and not stored[0].downloaded
        torrent, release, bangumi = seen[0]
        assert isinstance(torrent, TorrentInfo) and torrent.name == TORRENT_NAME
        assert isinstance(release, ParsedRelease) and release.episode == 12
        assert isinstance(bangumi, BangumiInfo)
        assert bangumi.title_raw == "Mushoku Tensei"

    async def test_accept_downloads(self, rss_engine, plugins):
        await seed(rss_engine)
        add_hook(plugins.registry, points.TORRENT_FILTER, lambda *a: True)
        client = await refresh_with(
            rss_engine, [Torrent(name=TORRENT_NAME, url="https://e/1.torrent")]
        )
        client.add_torrent.assert_called_once()

    async def test_fail_open_on_plugin_error(self, rss_engine, plugins):
        await seed(rss_engine)

        def boom(*args):
            raise RuntimeError("bad plugin")

        add_hook(plugins.registry, points.TORRENT_FILTER, boom)
        client = await refresh_with(
            rss_engine, [Torrent(name=TORRENT_NAME, url="https://e/1.torrent")]
        )
        client.add_torrent.assert_called_once()

    async def test_exclude_filter_runs_before_hooks(self, rss_engine, plugins):
        await seed(rss_engine, filter="1080")
        hook = MagicMock(return_value=True)
        add_hook(plugins.registry, points.TORRENT_FILTER, hook)
        client = await refresh_with(
            rss_engine, [Torrent(name=TORRENT_NAME, url="https://e/1.torrent")]
        )
        client.add_torrent.assert_not_called()
        hook.assert_not_called()

    async def test_no_hook_fast_path_skips_snapshots(self, rss_engine, no_runner):
        await seed(rss_engine)
        with patch(
            "module.rss.engine.torrent_info", side_effect=AssertionError("called")
        ):
            client = await refresh_with(
                rss_engine, [Torrent(name=TORRENT_NAME, url="https://e/1.torrent")]
            )
        client.add_torrent.assert_called_once()

    async def test_download_bangumi_applies_filter(self, rss_engine, plugins):
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        add_hook(
            plugins.registry,
            points.TORRENT_FILTER,
            lambda t, r, b: "- 12" not in t.name,
        )
        torrents = [
            Torrent(name=TORRENT_NAME, url="https://e/12.torrent"),
            Torrent(
                name="[Sub] Mushoku Tensei - 11 [1080p].mkv", url="https://e/11.torrent"
            ),
        ]
        req = AsyncMock()
        req.get_torrents = AsyncMock(return_value=torrents)
        client = AsyncMock()
        client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
        with (
            patch("module.rss.engine.RequestContent") as MockReq,
            patch("module.rss.engine.DownloadClient") as MockClient,
        ):
            MockReq.return_value.__aenter__ = AsyncMock(return_value=req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            await rss_engine.download_bangumi(bangumi)
        sent = client.add_torrent.call_args.args[0]
        assert [t.url for t in sent] == ["https://e/11.torrent"]


# ---------------------------------------------------------------- title.parsed


class TestTitleParsed:
    RAW = "[Lilith-Raws] Mushoku Tensei - 11 [1080p].mkv"

    async def parse(self) -> Bangumi:
        with patch.object(settings, "llm", LLM(enable=False)):
            result = await TitleParser.raw_parser(self.RAW)
        assert isinstance(result, Bangumi)
        return result

    async def test_hook_rewrites_release(self, plugins):
        baseline = await self.parse()
        received = []

        def fix(release):
            received.append(release)
            return replace(release, group="Alias", season=2)

        add_hook(plugins.registry, points.TITLE_PARSED, fix)
        result = await self.parse()
        assert isinstance(received[0], ParsedRelease)
        assert result.group_name == "Alias"
        assert result.season == 2
        assert result.title_raw == baseline.title_raw

    async def test_bad_hook_keeps_release(self, plugins):
        baseline = await self.parse()

        def boom(release):
            raise ValueError("bad")

        add_hook(plugins.registry, points.TITLE_PARSED, boom, "a")
        add_hook(plugins.registry, points.TITLE_PARSED, lambda r: {"x": 1}, "b")
        result = await self.parse()
        assert result.model_dump() == baseline.model_dump()

    async def test_hook_can_block_admission(self, plugins):
        from module.parser.analyser.tokenizer import MediaType

        add_hook(
            plugins.registry,
            points.TITLE_PARSED,
            lambda r: replace(r, media_type=MediaType.PV),
        )
        with patch.object(settings, "llm", LLM(enable=False)):
            assert await TitleParser.raw_parser(self.RAW) is None


# ---------------------------------------------------------------- torrent.adding


@pytest.fixture
def download_client(mock_qb_client):
    from module.downloader.download_client import DownloadClient

    with patch(
        "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
        return_value=mock_qb_client,
    ):
        client = DownloadClient()
    client.client = mock_qb_client
    mock_qb_client.add_torrents.return_value = AddResult.ADDED
    return client


async def add_magnet(client, bangumi):
    torrent = make_torrent(url="magnet:?xt=urn:btih:abc")
    with patch("module.downloader.download_client.RequestContent") as MockReq:
        MockReq.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        MockReq.return_value.__aexit__ = AsyncMock(return_value=False)
        return await client.add_torrent(torrent, bangumi)


class TestTorrentAdding:
    async def test_no_hook_keeps_defaults(self, download_client, mock_qb_client):
        bangumi = make_bangumi(id=7)
        assert await add_magnet(download_client, bangumi) is AddResult.ADDED
        kwargs = mock_qb_client.add_torrents.call_args.kwargs
        assert kwargs["category"] == "Bangumi"
        assert kwargs["tags"] == "ab:7"
        assert kwargs["save_path"] == bangumi.save_path

    async def test_hook_modifies_request_and_tag_restored(
        self, plugins, download_client, mock_qb_client
    ):
        received: list[AddRequest] = []

        def adjust(request: AddRequest) -> AddRequest:
            received.append(request)
            return replace(
                request,
                category="Anime",
                save_path=request.save_path + "-x",
                tags=("hevc",),
            )

        add_hook(plugins.registry, points.TORRENT_ADDING, adjust)
        bangumi = make_bangumi(id=7)
        original_path = bangumi.save_path
        assert original_path is not None
        await add_magnet(download_client, bangumi)
        kwargs = mock_qb_client.add_torrents.call_args.kwargs
        assert kwargs["category"] == "Anime"
        assert kwargs["save_path"] == original_path + "-x"
        assert kwargs["tags"] == "ab:7,hevc"
        assert received[0].tags == ("ab:7",)
        assert received[0].bangumi.id == 7
        assert received[0].torrents[0].url == "magnet:?xt=urn:btih:abc"
        # 宿主的 bangumi 对象不被修改
        assert bangumi.save_path == original_path

    async def test_failing_hook_falls_back(
        self, plugins, download_client, mock_qb_client
    ):
        def boom(request):
            raise RuntimeError("bad")

        add_hook(plugins.registry, points.TORRENT_ADDING, boom)
        await add_magnet(download_client, make_bangumi(id=3))
        kwargs = mock_qb_client.add_torrents.call_args.kwargs
        assert (kwargs["category"], kwargs["tags"]) == ("Bangumi", "ab:3")


# ---------------------------------------------------------------- http.request


class TestHttpRequest:
    async def fetch(self, url="https://pt.example/rss"):
        from module.network.request_url import RequestURL

        req = RequestURL()
        response = MagicMock()
        req._client = MagicMock()
        req._client.get = AsyncMock(return_value=response)
        await req.get_url(url)
        return req._client.get.call_args.kwargs["headers"]

    async def test_no_hook_default_headers(self, no_runner):
        headers = await self.fetch()
        assert "Cookie" not in headers
        assert headers["User-Agent"]

    async def test_hook_adds_cookie_per_host(self, plugins):
        def cookie(request: HttpRequest):
            if "pt.example" not in request.url:
                return None
            return replace(request, headers={**request.headers, "Cookie": "uid=1"})

        add_hook(plugins.registry, points.HTTP_REQUEST, cookie)
        assert (await self.fetch())["Cookie"] == "uid=1"
        assert "Cookie" not in await self.fetch("https://mikanani.me/rss")

    async def test_failing_hook_keeps_headers(self, plugins):
        def boom(request):
            raise RuntimeError("bad")

        add_hook(plugins.registry, points.HTTP_REQUEST, boom)
        headers = await self.fetch()
        assert "Cookie" not in headers and headers["User-Agent"]


# ---------------------------------------------------------------- metadata


class FakeMetadata:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.requests: list[MetadataRequest] = []

    async def enrich(self, request: MetadataRequest):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def add_metadata(registry, provider_id, impl, plugin_id="ext"):
    registry.add_provider(
        points.METADATA_PROVIDER, ProviderEntry(plugin_id, provider_id, lambda: impl)
    )


class TestMetadataProvider:
    async def test_plugin_provider_selected_by_rss_parser(self, plugins):
        impl = FakeMetadata()
        impl.result = Metadata(
            official_title="葬送的芙莉莲", season=2, year="2023", poster_link="p.jpg"
        )
        add_metadata(plugins.registry, "bgm", impl)
        bangumi = make_bangumi(official_title="Frieren", season=1, year=None)
        await RSSAnalyser().official_title_parser(
            bangumi, make_rss_item(parser="bgm"), make_torrent()
        )
        assert (bangumi.official_title, bangumi.season, bangumi.year) == (
            "葬送的芙莉莲",
            2,
            "2023",
        )
        assert bangumi.poster_link == "p.jpg"
        request = impl.requests[0]
        assert request.kind == "bangumi"
        assert request.current.official_title == "Frieren"

    async def test_plugin_provider_failure_keeps_values(self, plugins):
        add_metadata(plugins.registry, "bgm", FakeMetadata(error=RuntimeError("x")))
        bangumi = make_bangumi(official_title="Frieren")
        for _ in range(3):
            await RSSAnalyser().official_title_parser(
                bangumi, make_rss_item(parser="bgm"), make_torrent()
            )
        assert bangumi.official_title == "Frieren"
        assert plugins.tripped == ["ext"]

    async def test_plugin_provider_wrong_type_ignored(self, plugins):
        add_metadata(plugins.registry, "bgm", FakeMetadata(result={"title": "x"}))
        movie_rss = make_rss_item(parser="bgm")
        bangumi = make_bangumi(official_title="Frieren")
        await RSSAnalyser().official_title_parser(bangumi, movie_rss, make_torrent())
        assert bangumi.official_title == "Frieren"

    async def test_unknown_parser_is_noop(self, plugins):
        bangumi = make_bangumi(official_title="A.B", poster_link="x")
        await RSSAnalyser().official_title_parser(
            bangumi, make_rss_item(parser="none"), make_torrent()
        )
        assert (bangumi.official_title, bangumi.poster_link) == ("A B", "x")

    async def test_movie_metadata(self, plugins):
        from module.models import Movie

        add_metadata(
            plugins.registry,
            "bgm",
            FakeMetadata(Metadata(official_title="Movie", year="2020")),
        )
        movie = Movie(official_title="Raw", title_raw="Raw", year=None)
        await RSSAnalyser().official_title_parser_movie(
            movie, make_rss_item(parser="bgm"), make_torrent()
        )
        assert (movie.official_title, movie.year) == ("Movie", 2020)

    async def test_core_tmdb_miss_resets_year(self, plugins):
        """与 3.x 一致：TMDB 未命中时沿用原标题，年份与海报被置空。"""
        bangumi = make_bangumi(official_title="Frieren", year="2023", season=1)
        with patch.object(
            TitleParser,
            "tmdb_parser",
            AsyncMock(return_value=("Frieren", 1, None, None)),
        ) as tmdb:
            await RSSAnalyser().official_title_parser(
                bangumi, make_rss_item(parser="tmdb"), make_torrent()
            )
        assert tmdb.call_args.args[:2] == ("Frieren", 1)
        assert (bangumi.year, bangumi.poster_link) == (None, None)

    async def test_core_mikan_keeps_title_when_empty(self, plugins):
        bangumi = make_bangumi(official_title="Frieren", year="2023")
        with patch.object(
            TitleParser, "mikan_parser", AsyncMock(return_value=("poster.jpg", ""))
        ):
            await RSSAnalyser().official_title_parser(
                bangumi, make_rss_item(parser="mikan"), make_torrent()
            )
        assert (bangumi.official_title, bangumi.poster_link, bangumi.year) == (
            "Frieren",
            "poster.jpg",
            "2023",
        )

    async def test_core_mikan_errors_still_propagate(self, plugins):
        bangumi = make_bangumi()
        with (
            patch.object(
                TitleParser, "mikan_parser", AsyncMock(side_effect=KeyError("x"))
            ),
            pytest.raises(KeyError),
        ):
            await RSSAnalyser().official_title_parser(
                bangumi, make_rss_item(parser="mikan"), make_torrent()
            )

    async def test_fetch_poster_false_skips_provider(self, plugins):
        impl = FakeMetadata(Metadata(official_title="X"))
        add_metadata(plugins.registry, "bgm", impl)
        bangumi = make_bangumi(official_title="Frieren")
        await RSSAnalyser().official_title_parser(
            bangumi, make_rss_item(parser="bgm"), make_torrent(), fetch_poster=False
        )
        assert impl.requests == []


# ---------------------------------------------------------------- built-in plugin


def load_builtin():
    candidates, errors = discover(
        local_root=BUILTIN_ROOT / "__missing__", entry_point_group="ab-test-none"
    )
    assert errors == []
    return {c.manifest.id: c for c in candidates}["ingest-filters"]


TORRENT = TorrentInfo(name="[Sub] Show - 01 [1080p][简体].mkv", url="u")
BANGUMI = BangumiInfo(id=1, official_title="Show", title_raw="Show", season=1)


class TestIngestFiltersPlugin:
    def plugin_cls(self):
        return load_builtin().load()

    def test_discovered_as_builtin(self):
        candidate = load_builtin()
        assert candidate.source == "builtin" and candidate.signed

    def test_empty_config_is_noop(self, tmp_path):
        plugin, _ = create_plugin(self.plugin_cls(), {}, data_dir=tmp_path)
        assert plugin.include_regex(TORRENT, None, BANGUMI).accept

    def test_include_regex(self, tmp_path):
        cls = self.plugin_cls()
        plugin, _ = create_plugin(cls, {"include": ["720p", "简体"]}, data_dir=tmp_path)
        assert plugin.include_regex(TORRENT, None, BANGUMI).accept
        plugin, _ = create_plugin(cls, {"include": ["2160P "]}, data_dir=tmp_path)
        verdict = plugin.include_regex(TORRENT, None, BANGUMI)
        assert not verdict.accept and verdict.reason

    def test_invalid_regex_falls_back_to_literal(self, tmp_path):
        plugin, _ = create_plugin(
            self.plugin_cls(), {"include": ["[简体"]}, data_dir=tmp_path
        )
        assert plugin.include_regex(TORRENT, None, BANGUMI).accept

    async def test_loaded_by_manager_enabled_by_default(self, plugins, tmp_path):
        settings_obj = SimpleNamespace(
            plugins=Plugins(options={"ingest-filters": {"include": ["2160p"]}})
        )
        manager = PluginManager(
            settings_obj,
            registry=plugins.registry,
            discover_fn=lambda: ([load_builtin()], []),
            data_root=tmp_path,
        )
        await manager.start()
        try:
            status = {s.id: s for s in manager.statuses()}["ingest-filters"]
            assert status.state == "active"
            assert status.config_schema is not None
            assert "include" in status.config_schema["properties"]
            verdict = await manager.runner.filter(
                points.TORRENT_FILTER, TORRENT, None, BANGUMI
            )
            assert not verdict.accept
        finally:
            await manager.stop()
        assert not plugins.registry.has_hooks(points.TORRENT_FILTER)

    async def test_default_config_does_not_change_refresh(
        self, rss_engine, plugins, tmp_path
    ):
        manager = PluginManager(
            SimpleNamespace(plugins=Plugins()),
            registry=plugins.registry,
            discover_fn=lambda: ([load_builtin()], []),
            data_root=tmp_path,
        )
        await manager.start()
        try:
            await seed(rss_engine)
            client = await refresh_with(
                rss_engine, [Torrent(name=TORRENT_NAME, url="https://e/1.torrent")]
            )
        finally:
            await manager.stop()
        client.add_torrent.assert_called_once()
