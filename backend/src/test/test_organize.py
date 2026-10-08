"""P4 整理流水线：rename_strategy 扩展点、file.renamed / torrent.organized 事件、
内置 rename-template 与 media-server-refresh 插件。"""

import asyncio
import itertools
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ab_sdk import Event, points
from ab_sdk.organize import FileRenamed, TorrentOrganized
from ab_sdk.rename import RenameInput
from ab_sdk.testing import create_plugin
from module.downloader import DownloadClient
from module.manager.rename_strategy import (
    CORE_STRATEGIES,
    build_input,
    format_episode,
    gen_path,
)
from module.manager.renamer import BangumiLink, Renamer
from module.models import EpisodeFile, SubtitleFile
from module.models.config import Plugins
from module.plugin import PluginManager, host
from module.plugin.bus import EventBus
from module.plugin.loader import BUILTIN_ROOT, discover
from module.plugin.registry import ProviderEntry


@pytest.fixture
def registry(monkeypatch):
    """每个测试一个全新的进程级注册表（含 core 登记）。"""
    monkeypatch.setattr(host, "_registry", None)
    return host.get_registry()


@pytest.fixture
def bus(monkeypatch):
    """把进程级总线指向一个新的 EventBus，并记录收到的全部事件。"""
    event_bus = EventBus()
    received: list[Event] = []
    event_bus.subscribe("*", received.append)
    monkeypatch.setattr(host, "_bus", event_bus)
    event_bus.received = received  # type: ignore[attr-defined]
    yield event_bus


def load_builtin(plugin_id: str):
    candidates, errors = discover(
        local_root=Path("/nonexistent"), entry_point_group="ab-test-none"
    )
    assert errors == []
    by_id = {c.manifest.id: c for c in candidates}
    return by_id[plugin_id].load()


# ---------------------------------------------------------------- equivalence


def _legacy_format_episode(episode):
    if isinstance(episode, float) and episode.is_integer():
        episode = int(episode)
    return f"0{episode}" if episode < 10 else str(episode)


def _legacy_adjust_episode(original, episode_offset):
    if original == 0 and episode_offset != 0:
        return 0
    adjusted = original + episode_offset
    if adjusted < 0 or (adjusted == 0 and original > 0):
        return original
    return adjusted


def _legacy_gen_path(file_info, bangumi_name, method, episode_offset=0):
    """3.3 的 Renamer.gen_path 原样拷贝（字幕使用 subtitle_ 前缀方法），作为
    插件化之后内置策略的对照基准。"""
    season_num = file_info.season
    season = f"0{season_num}" if season_num < 10 else season_num
    episode = _legacy_format_episode(
        _legacy_adjust_episode(file_info.episode, episode_offset)
    )
    if method == "none" or method == "subtitle_none":
        return file_info.media_path
    title = file_info.title
    if file_info.episode_type == "movie":
        base = bangumi_name if "advance" in method else title
        if method.startswith("subtitle_"):
            return f"{base}.{file_info.language}{file_info.suffix}"
        return f"{base}{file_info.suffix}"
    elif method == "pn":
        return f"{title} S{season}E{episode}{file_info.suffix}"
    elif method == "advance":
        return f"{bangumi_name} S{season}E{episode}{file_info.suffix}"
    elif method == "subtitle_pn":
        return f"{title} S{season}E{episode}.{file_info.language}{file_info.suffix}"
    elif method == "subtitle_advance":
        return (
            f"{bangumi_name} S{season}E{episode}.{file_info.language}{file_info.suffix}"
        )
    return file_info.media_path


EPISODES = [0, 1, 5, 9, 10, 12, 99, 100, 5.5, 12.5, 13.0]
SEASONS = [0, 1, 9, 10, 12]
OFFSETS = [0, -12, 12, -4]
TITLES = [("My Anime", "My Anime (2024)"), ("Re:Zero 第二季", "Re:Zero (2020)")]


def _files(kind, episode_type):
    for (title, _), season, episode in itertools.product(TITLES, SEASONS, EPISODES):
        common = dict(
            title=title,
            season=season,
            episode=episode,
            episode_type=episode_type,
            group="Sub",
        )
        if kind == "media":
            for suffix in (".mkv", ".mp4"):
                yield EpisodeFile(
                    media_path=f"dir/raw{suffix}", suffix=suffix, **common
                )
        else:
            for language, suffix in (("zh", ".ass"), ("zh-tw", ".srt")):
                yield SubtitleFile(
                    media_path=f"dir/raw.{language}{suffix}",
                    language=language,
                    suffix=suffix,
                    **common,
                )


@pytest.mark.parametrize("method", ["pn", "advance", "none"])
@pytest.mark.parametrize("kind", ["media", "subtitle"])
@pytest.mark.parametrize("episode_type", ["episode", "movie", "special"])
def test_core_strategies_match_legacy_gen_path(registry, method, kind, episode_type):
    legacy_method = f"subtitle_{method}" if kind == "subtitle" else method
    checked = 0
    for file_info in _files(kind, episode_type):
        for (_, bangumi_name), offset in itertools.product(TITLES, OFFSETS):
            expected = _legacy_gen_path(file_info, bangumi_name, legacy_method, offset)
            assert gen_path(file_info, bangumi_name, method, offset) == expected, (
                file_info,
                bangumi_name,
                offset,
            )
            checked += 1
    assert checked > 1000


def test_core_strategies_registered_as_core(registry):
    providers = registry.providers(points.RENAME_STRATEGY)
    assert set(providers) == {"pn", "advance", "none"}
    assert all(e.plugin_id == host.CORE for e in providers.values())
    assert host.plugin_provider_ids(points.RENAME_STRATEGY) == []


# ---------------------------------------------------------------- dispatch


EP = EpisodeFile(
    media_path="raw/[Sub] Anime - 05.mkv",
    title="Anime",
    season=1,
    episode=5,
    suffix=".mkv",
)


def _add_strategy(registry, provider_id, impl, plugin_id="ext"):
    registry.add_provider(
        points.RENAME_STRATEGY, ProviderEntry(plugin_id, provider_id, lambda: impl)
    )


def test_unknown_method_keeps_path_and_logs(registry, caplog):
    with caplog.at_level(logging.ERROR):
        assert gen_path(EP, "Anime (2024)", "nope") == EP.media_path
    assert "Unknown rename method: nope" in caplog.text


def test_plugin_strategy_receives_offset_adjusted_input(registry):
    seen: list[RenameInput] = []

    class Upper:
        def target_name(self, f: RenameInput) -> str:
            seen.append(f)
            return f"{f.title.upper()} {f.episode}{f.full_suffix}"

    _add_strategy(registry, "upper", Upper())
    assert gen_path(EP, "Anime (2024)", "upper", episode_offset=2) == "ANIME 7.mkv"
    assert seen == [
        RenameInput(
            title="Anime",
            bangumi_name="Anime (2024)",
            season=1,
            episode=7,
            suffix=".mkv",
            kind="media",
            language=None,
            episode_type="episode",
            original_path="raw/[Sub] Anime - 05.mkv",
            group=None,
        )
    ]


@pytest.mark.parametrize(
    "result", ["", "   ", None, 42, "/abs/x.mkv", "../escape.mkv", "a/../../b.mkv"]
)
def test_invalid_strategy_result_keeps_path(registry, caplog, result):
    class Bad:
        def target_name(self, f):
            return result

    _add_strategy(registry, "bad", Bad())
    with caplog.at_level(logging.ERROR):
        assert gen_path(EP, "Anime", "bad") == EP.media_path
    assert "invalid path" in caplog.text


def test_raising_strategy_keeps_path(registry, caplog):
    class Boom:
        def target_name(self, f):
            raise RuntimeError("kaput")

    _add_strategy(registry, "boom", Boom())
    with caplog.at_level(logging.ERROR):
        assert gen_path(EP, "Anime", "boom") == EP.media_path
    assert "kaput" in caplog.text


def test_subdirectory_result_is_allowed(registry):
    class Nested:
        def target_name(self, f):
            return f"Extras/{f.title}{f.suffix}"

    _add_strategy(registry, "nested", Nested())
    assert gen_path(EP, "Anime", "nested") == "Extras/Anime.mkv"


def test_full_suffix():
    sub = SubtitleFile(
        media_path="a.ass",
        title="A",
        season=1,
        episode=1,
        language="zh-tw",
        suffix=".ass",
    )
    assert build_input(sub, "A").full_suffix == ".zh-tw.ass"
    assert build_input(EP, "A").full_suffix == ".mkv"
    assert set(CORE_STRATEGIES) == {"pn", "advance", "none"}


# ---------------------------------------------------------------- host bus


async def test_publish_without_bus_is_noop(monkeypatch):
    monkeypatch.setattr(host, "_bus", None)
    host.publish(TorrentOrganized("h", "n", None, "T", "/p"))


async def test_publish_swallows_bus_errors(monkeypatch, caplog):
    broken = MagicMock()
    broken.publish.side_effect = RuntimeError("bus down")
    monkeypatch.setattr(host, "_bus", broken)
    with caplog.at_level(logging.ERROR):
        host.publish(TorrentOrganized("h", "n", None, "T", "/p"))
    assert "torrent.organized" in caplog.text


def test_publish_without_event_loop_is_quiet(monkeypatch, caplog):
    """同步上下文里订阅者的 worker 无法启动：丢弃事件，只记 debug 日志。"""
    from module.plugin.bus import EventBus

    bus = EventBus()
    bus.subscribe(TorrentOrganized.kind, lambda event: None)
    monkeypatch.setattr(host, "_bus", bus)
    with caplog.at_level(logging.DEBUG):
        host.publish(TorrentOrganized("h", "n", None, "T", "/p"))
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert "无事件循环" in caplog.text


async def test_plugin_manager_owns_process_bus(monkeypatch, tmp_path):
    monkeypatch.setattr(host, "_bus", None)
    manager = PluginManager(
        SimpleNamespace(plugins=Plugins()),
        discover_fn=lambda: ([], []),
        data_root=tmp_path,
    )
    await manager.start()
    assert host.get_bus() is manager.bus
    await manager.stop()
    assert host.get_bus() is None


# ---------------------------------------------------------------- renamer events


SAVE_PATH = "/downloads/Bangumi/Anime (2024)/Season 1"


@pytest.fixture
def renamer(mock_qb_client):
    with patch("module.downloader.download_client.settings") as mock_settings:
        mock_settings.downloader.type = "qbittorrent"
        mock_settings.downloader.host = "localhost:8080"
        mock_settings.downloader.username = "admin"
        mock_settings.downloader.password = "admin"
        mock_settings.downloader.ssl = False
        mock_settings.downloader.path = "/downloads/Bangumi"
        with patch(
            "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
            return_value=mock_qb_client,
        ):
            client = DownloadClient()
    client.client = mock_qb_client
    return Renamer(client)


async def _run(renamer, files, parser, *, method="pn", link=None):
    renamer.client.client.torrents_info.return_value = [
        {"hash": "h1", "name": "[Sub] Anime - 01", "save_path": SAVE_PATH, "tags": ""}
    ]
    renamer.client.client.torrents_files.return_value = files
    link = link or BangumiLink(bangumi_id=7, official_title="Anime Official")
    with (
        patch.object(renamer._parser, "torrent_parser", side_effect=parser),
        patch.object(
            renamer, "_batch_lookup_offsets", AsyncMock(return_value={"h1": link})
        ),
        patch("module.manager.renamer.settings") as mock_settings,
        patch("module.downloader.path.settings") as mock_path_settings,
    ):
        mock_settings.bangumi_manage.rename_method = method
        mock_settings.bangumi_manage.remove_bad_torrent = False
        mock_path_settings.downloader.path = "/downloads/Bangumi"
        return await renamer.rename()


def _parser(torrent_path, season, file_type="media", **kwargs):
    episode = int(torrent_path.split(" - ")[1][:2])
    if file_type == "subtitle":
        return SubtitleFile(
            media_path=torrent_path,
            title="Anime",
            season=season,
            episode=episode,
            language="zh",
            suffix=".ass",
        )
    return EpisodeFile(
        media_path=torrent_path,
        title="Anime",
        season=season,
        episode=episode,
        suffix=".mkv",
    )


async def test_single_file_publishes_file_and_torrent_events(renamer, bus):
    files = [{"name": "[Sub] Anime - 01.mkv"}, {"name": "[Sub] Anime - 01.ass"}]
    result = await _run(
        renamer,
        files,
        _parser,
        link=BangumiLink(episode_offset=11, bangumi_id=7, official_title="Anime O"),
    )
    await bus.drain()

    assert len(result) == 1
    assert bus.received == [
        FileRenamed(
            torrent_hash="h1",
            bangumi_id=7,
            official_title="Anime O",
            season=1,
            episode=12,
            old_path="[Sub] Anime - 01.mkv",
            new_path="Anime S01E12.mkv",
            save_path=SAVE_PATH,
            file_kind="media",
        ),
        FileRenamed(
            torrent_hash="h1",
            bangumi_id=7,
            official_title="Anime O",
            season=1,
            episode=12,
            old_path="[Sub] Anime - 01.ass",
            new_path="Anime S01E12.zh.ass",
            save_path=SAVE_PATH,
            file_kind="subtitle",
        ),
        TorrentOrganized(
            torrent_hash="h1",
            torrent_name="[Sub] Anime - 01",
            bangumi_id=7,
            official_title="Anime O",
            save_path=SAVE_PATH,
            collection=False,
        ),
    ]


async def test_unmatched_bangumi_falls_back_to_folder_name(renamer, bus):
    await _run(renamer, [{"name": "[Sub] Anime - 01.mkv"}], _parser, link=BangumiLink())
    await bus.drain()
    renamed = [e for e in bus.received if isinstance(e, FileRenamed)]
    assert [(e.bangumi_id, e.official_title) for e in renamed] == [
        (None, "Anime (2024)")
    ]


async def test_collection_publishes_each_file_then_organized(renamer, bus):
    files = [{"name": "[Sub] Anime - 01.mkv"}, {"name": "[Sub] Anime - 02.mkv"}]
    await _run(renamer, files, _parser)
    await bus.drain()

    assert [type(e).__name__ for e in bus.received] == [
        "FileRenamed",
        "FileRenamed",
        "TorrentOrganized",
    ]
    assert [e.new_path for e in bus.received[:2]] == [
        "Anime S01E01.mkv",
        "Anime S01E02.mkv",
    ]
    assert bus.received[2].collection is True


async def test_failed_rename_publishes_nothing(renamer, bus):
    renamer.client.client.torrents_rename_file.return_value = False
    await _run(renamer, [{"name": "[Sub] Anime - 01.mkv"}], _parser)
    await bus.drain()
    assert bus.received == []


async def test_none_method_publishes_nothing(renamer, bus):
    await _run(renamer, [{"name": "[Sub] Anime - 01.mkv"}], _parser, method="none")
    await bus.drain()
    assert bus.received == []


async def test_already_named_file_publishes_only_organized(renamer, bus):
    def parser(torrent_path, season, **kwargs):
        return EpisodeFile(
            media_path=torrent_path,
            title="Anime",
            season=season,
            episode=1,
            suffix=".mkv",
        )

    await _run(renamer, [{"name": "Anime S01E01.mkv"}], parser)
    await bus.drain()
    assert [type(e).__name__ for e in bus.received] == ["TorrentOrganized"]


async def test_publish_failure_never_breaks_rename(renamer, monkeypatch):
    broken = MagicMock()
    broken.publish.side_effect = RuntimeError("bus down")
    monkeypatch.setattr(host, "_bus", broken)
    result = await _run(renamer, [{"name": "[Sub] Anime - 01.mkv"}], _parser)
    assert len(result) == 1
    renamer.client.client.add_tag.assert_awaited_once_with("h1", "ab:renamed")


# ---------------------------------------------------------------- rename-template


@pytest.fixture
def template_plugin():
    return load_builtin("rename-template")


def _strategy(cls, options=None):
    plugin, _ = create_plugin(cls, options or {}, plugin_id="rename-template")
    return plugin.strategy()


def test_template_default_matches_pn(template_plugin, registry):
    strategy = _strategy(template_plugin)
    for kind in ("media", "subtitle"):
        for episode_type in ("episode", "movie", "special"):
            for file_info in _files(kind, episode_type):
                f = build_input(file_info, "Anime (2024)", 0)
                assert strategy.target_name(f) == CORE_STRATEGIES["pn"].target_name(f)


def test_template_custom_format(template_plugin):
    strategy = _strategy(
        template_plugin,
        {
            "template": "[{{ group }}] {{ bangumi_name }} - {{ episode|pad(3) }}",
            "movie_template": "{{ bangumi_name }} [Movie]",
        },
    )
    ep = EpisodeFile(
        media_path="x.mkv", title="A", season=2, episode=5.5, suffix=".mkv", group="G"
    )
    assert (
        strategy.target_name(build_input(ep, "A (2024)")) == "[G] A (2024) - 005.5.mkv"
    )
    movie = ep.model_copy(update={"episode_type": "movie"})
    assert (
        strategy.target_name(build_input(movie, "A (2024)")) == "A (2024) [Movie].mkv"
    )


@pytest.mark.parametrize(
    "template",
    [
        "{{ title }}/S{{ season }}",  # 路径分隔符
        "{{ bangumi_name }}\\{{ title }}",
        "{% if false %}x{% endif %}  ",  # 空结果
        "{{ titel }}",  # 拼错的变量
        "{{ title.__class__.__mro__ }}",  # 沙箱拒绝
        "{{ season|pad('x') }}",
    ],
)
def test_template_bad_render_keeps_path(template_plugin, registry, caplog, template):
    _add_strategy(
        registry, "template", _strategy(template_plugin, {"template": template})
    )
    with caplog.at_level(logging.ERROR):
        assert gen_path(EP, "Anime", "template") == EP.media_path
    assert "Rename method template failed" in caplog.text


@pytest.mark.parametrize("template", ["{{ title ", "{% for %}", "  "])
def test_template_syntax_rejected_on_save(template_plugin, template):
    with pytest.raises(ValueError):
        template_plugin.config_model.model_validate({"template": template})


def test_template_pad_filter(template_plugin):
    import sys

    pad = sys.modules[template_plugin.__module__].pad
    assert [pad(v) for v in (1, 9, 10, 100, 5.5, 12.5, 13.0)] == [
        format_episode(v) for v in (1, 9, 10, 100, 5.5, 12.5, 13.0)
    ]
    assert pad(7, 3) == "007"


async def test_builtin_plugins_load_through_manager(registry, monkeypatch, tmp_path):
    monkeypatch.setattr(host, "_bus", None)
    manager = PluginManager(
        SimpleNamespace(plugins=Plugins()),
        registry=registry,
        discover_fn=lambda: discover(
            local_root=tmp_path / "none", entry_point_group="ab-test-none"
        ),
        data_root=tmp_path,
    )
    await manager.start()
    try:
        states = {s.id: (s.source, s.state) for s in manager.statuses()}
        assert states["rename-template"] == ("builtin", "active")
        assert states["media-server-refresh"] == ("builtin", "active")
        assert host.plugin_provider_ids(points.RENAME_STRATEGY) == ["template"]
        assert gen_path(EP, "Anime", "template") == "Anime S01E05.mkv"
    finally:
        await manager.stop()
    assert host.plugin_provider_ids(points.RENAME_STRATEGY) == []


def test_builtin_root_contains_p4_plugins():
    assert (BUILTIN_ROOT / "rename-template" / "plugin.toml").is_file()
    assert (BUILTIN_ROOT / "media-server-refresh" / "plugin.toml").is_file()


# ---------------------------------------------------------------- media-server-refresh


def _event(n: int = 1) -> FileRenamed:
    return FileRenamed(
        torrent_hash="h",
        bangumi_id=1,
        official_title="A",
        season=1,
        episode=n,
        old_path="old.mkv",
        new_path=f"A S01E0{n}.mkv",
        save_path="/b",
        file_kind="media",
    )


def _refresh_plugin(options, tmp_path, handler=None):
    cls = load_builtin("media-server-refresh")
    plugin, ctx = create_plugin(cls, options, data_dir=tmp_path)
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request) if handler else httpx.Response(204)

    plugin.client_factory = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(record)
    )
    return plugin, requests


async def test_refresh_is_noop_until_configured(tmp_path):
    plugin, requests = _refresh_plugin({"url": "http://jf:8096"}, tmp_path)
    await plugin.setup()
    await plugin.on_file_renamed(_event())
    assert plugin._pending is None
    await plugin.teardown()
    assert requests == []


@pytest.mark.parametrize(
    ("server", "method", "url", "header", "value"),
    [
        (
            "jellyfin",
            "POST",
            "http://srv:8096/Library/Refresh",
            "authorization",
            'MediaBrowser Token="k3y"',
        ),
        ("emby", "POST", "http://srv:8096/emby/Library/Refresh", "x-emby-token", "k3y"),
        (
            "plex",
            "GET",
            "http://srv:8096/library/sections/all/refresh",
            "x-plex-token",
            "k3y",
        ),
    ],
)
async def test_refresh_coalesces_events(tmp_path, server, method, url, header, value):
    plugin, requests = _refresh_plugin(
        {"server": server, "url": "http://srv:8096/", "api_key": "k3y", "delay": 0.05},
        tmp_path,
    )
    for n in range(1, 4):
        await plugin.on_file_renamed(_event(n))
    await asyncio.wait_for(plugin._pending, 1)

    assert len(requests) == 1
    assert requests[0].method == method
    assert str(requests[0].url) == url
    assert requests[0].headers[header] == value
    # 刷新完成后的新事件会再排一次
    await plugin.on_file_renamed(_event(4))
    await asyncio.wait_for(plugin._pending, 1)
    assert len(requests) == 2


async def test_refresh_failure_is_logged_not_raised(tmp_path, caplog):
    plugin, requests = _refresh_plugin(
        {"url": "http://srv", "api_key": "k", "delay": 0},
        tmp_path,
        handler=lambda request: httpx.Response(401),
    )
    assert await plugin.refresh() is False

    def explode(request):
        raise httpx.ConnectError("refused")

    plugin2, _ = _refresh_plugin(
        {"url": "http://srv", "api_key": "s3cr3t-key", "delay": 0},
        tmp_path,
        handler=explode,
    )
    with caplog.at_level(logging.WARNING):
        await plugin2.on_file_renamed(_event())
        await asyncio.wait_for(plugin2._pending, 1)
    assert "刷新媒体库失败" in caplog.text
    assert "s3cr3t-key" not in caplog.text


async def test_teardown_cancels_pending_refresh(tmp_path):
    plugin, requests = _refresh_plugin(
        {"url": "http://srv", "api_key": "k", "delay": 60}, tmp_path
    )
    await plugin.on_file_renamed(_event())
    pending = plugin._pending
    await plugin.teardown()
    assert pending.cancelled()
    assert requests == []


def test_refresh_api_key_is_secret():
    cls = load_builtin("media-server-refresh")
    schema = cls.config_model.model_json_schema()
    assert schema["properties"]["api_key"]["secret"] is True
