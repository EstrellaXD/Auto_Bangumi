"""P4 organize 扩展点：rename_strategy 的解析、回退与跳过通知，conflict_policy，
以及 file.renamed / torrent.organized 事件。"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ab_sdk import points
from ab_sdk.events import (
    FileRenamed,
    OrganizedFile,
    RenameSkippedEvent,
    TorrentOrganized,
)
from ab_sdk.rename import (
    ConflictRequest,
    RenameInput,
    RenameSkipped,
    Revision,
    RevisionTask,
)
from ab_sdk.testing import RecordingBus, create_plugin
from module.downloader import DownloadClient
from module.manager import renamer as renamer_module
from module.manager.renamer import Renamer
from module.manager.revision_policy import CoreConflictPolicy
from module.models import EpisodeFile, SubtitleFile
from module.models.config import Plugins
from module.plugin import PluginManager, host
from module.plugin.loader import BUILTIN_ROOT, discover
from module.plugin.registry import ProviderEntry
from module.plugin.runner import CircuitBreaker, HookRunner

SAVE_PATH = "/downloads/Bangumi/Anime (2024)/Season 1"
NAME = "[Sub] Anime - 01.mkv"
INFO = {"hash": "h1", "name": NAME, "save_path": SAVE_PATH, "tags": "ab:7"}
SUB = "[Sub] Anime - 01.zh.ass"


def parse(torrent_path: str, **kwargs) -> EpisodeFile | SubtitleFile:
    if torrent_path == SUB:
        return SubtitleFile(
            media_path=SUB,
            title="Anime",
            season=1,
            episode=1,
            language="zh",
            suffix=".ass",
        )
    return EpisodeFile(
        media_path=torrent_path, title="Anime", season=1, episode=1, suffix=".mkv"
    )


@pytest.fixture
def plugins(monkeypatch):
    """全新的进程级注册表、runner 与记录事件的总线。"""
    monkeypatch.setattr(host, "_registry", None)
    registry = host.get_registry()
    tripped: list[str] = []
    breaker = CircuitBreaker(2, on_trip=lambda plugin_id, _: tripped.append(plugin_id))
    monkeypatch.setattr(host, "_runner", HookRunner(registry, breaker))
    bus = RecordingBus()
    monkeypatch.setattr(host, "_bus", bus)
    monkeypatch.setattr(renamer_module, "_organized_published", {})
    monkeypatch.setattr(renamer_module, "_skip_notified", set())
    return SimpleNamespace(registry=registry, tripped=tripped, bus=bus)


def add_strategy(registry, provider_id: str, target_name, plugin_id: str = "ext"):
    impl = SimpleNamespace(target_name=target_name)
    registry.add_provider(
        points.RENAME_STRATEGY, ProviderEntry(plugin_id, provider_id, lambda: impl)
    )


@pytest.fixture
def renamer(mock_qb_client):
    with patch("module.downloader.download_client.settings") as mock_settings:
        mock_settings.downloader.id = "default"
        mock_settings.downloader.type = "qbittorrent"
        mock_settings.downloader.host = "localhost:8080"
        mock_settings.downloader.path = "/downloads/Bangumi"
        with patch(
            "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
            return_value=mock_qb_client,
        ):
            client = DownloadClient()
    client.client = mock_qb_client
    mock_qb_client.torrents_info.return_value = [INFO]
    mock_qb_client.torrents_files.return_value = [
        {"name": NAME},
        {"name": SUB},
    ]
    return Renamer(client)


async def run(renamer: Renamer, method: str) -> None:
    with (
        patch.object(renamer._parser, "torrent_parser", side_effect=parse),
        patch("module.manager.renamer.settings") as mock_settings,
        patch("module.downloader.path.settings") as mock_path_settings,
    ):
        mock_settings.plugins.slots.rename_strategy = method
        mock_settings.bangumi_manage.remove_bad_torrent = False
        mock_path_settings.downloader.path = "/downloads/Bangumi"
        await renamer.rename()


def published(bus: RecordingBus, cls: type) -> list:
    return [e for e in bus.published if isinstance(e, cls)]


async def test_rename_unregistered_method_keeps_names_without_tag(plugins, renamer):
    await run(renamer, "jellyfin-style")

    renamer.client.client.torrents_rename_file.assert_not_called()
    renamer.client.client.add_tag.assert_not_called()
    assert published(plugins.bus, TorrentOrganized)


async def test_rename_plugin_strategy_renames_and_publishes_events(plugins, renamer):
    seen: list[RenameInput] = []

    def target_name(f: RenameInput) -> str:
        seen.append(f)
        language = f".{f.language}" if f.kind == "subtitle" else ""
        return f"{f.title} E{f.episode}{language}{f.suffix}"

    add_strategy(plugins.registry, "custom", target_name)
    await run(renamer, "custom")

    assert [(f.kind, f.bangumi_name) for f in seen] == [
        ("media", "Anime (2024)"),
        ("subtitle", "Anime (2024)"),
    ]
    renamer.client.client.add_tag.assert_awaited_once_with("h1", "ab:renamed")
    assert published(plugins.bus, FileRenamed) == [
        FileRenamed(
            bangumi_id=7,
            old_path=f"{SAVE_PATH}/{NAME}",
            new_path=f"{SAVE_PATH}/Anime E1.mkv",
            file_kind="media",
        ),
        FileRenamed(
            bangumi_id=7,
            old_path=f"{SAVE_PATH}/{SUB}",
            new_path=f"{SAVE_PATH}/Anime E1.zh.ass",
            file_kind="subtitle",
        ),
    ]
    assert published(plugins.bus, TorrentOrganized) == [
        TorrentOrganized(
            torrent_hash="h1",
            bangumi_id=7,
            files=(
                OrganizedFile(f"{SAVE_PATH}/Anime E1.mkv", "media"),
                OrganizedFile(f"{SAVE_PATH}/Anime E1.zh.ass", "subtitle"),
            ),
        )
    ]


async def test_rename_plugin_removed_mid_tick_keeps_tick_strategy(plugins, renamer):
    def target_name(f: RenameInput) -> str:
        # 本轮处理中插件被停用（重载、熔断）：策略已从注册表移除
        plugins.registry.remove_plugin("ext")
        language = f".{f.language}" if f.kind == "subtitle" else ""
        return f"{f.title} E{f.episode}{language}{f.suffix}"

    add_strategy(plugins.registry, "custom", target_name)
    await run(renamer, "custom")

    # 打 ab:renamed 标签与生成文件名必须来自同一个策略：字幕也按本轮策略改名
    renamed = [
        c.kwargs["new_path"]
        for c in renamer.client.client.torrents_rename_file.await_args_list
    ]
    assert renamed == ["Anime E1.mkv", "Anime E1.zh.ass"]
    renamer.client.client.add_tag.assert_awaited_once_with("h1", "ab:renamed")


async def test_rename_none_publishes_organized_once_per_process(plugins, renamer):
    await run(renamer, "none")
    await run(renamer, "none")

    renamer.client.client.torrents_rename_file.assert_not_called()
    assert published(plugins.bus, FileRenamed) == []
    organized = published(plugins.bus, TorrentOrganized)
    assert len(organized) == 1
    assert organized[0].files[0] == OrganizedFile(f"{SAVE_PATH}/{NAME}", "media")


def _skip(f: RenameInput) -> str:
    raise RenameSkipped("模板渲染失败：'titel' is undefined")


def _crash(f: RenameInput) -> str:
    raise ValueError("boom")


@pytest.mark.parametrize("with_runner", [True, False])
@pytest.mark.parametrize(
    ("target_name", "counted"),
    [(_skip, False), (_crash, True), (lambda f: "", True), (lambda f: 3, True)],
)
async def test_rename_strategy_failure_keeps_name_and_notifies_once(
    plugins, renamer, monkeypatch, target_name, counted, with_runner
):
    if not with_runner:
        # 未设置 runner（脚本、CLI）：插件失败只记录日志，不计入熔断
        monkeypatch.setattr(host, "_runner", None)
        counted = False
    add_strategy(plugins.registry, "custom", target_name)
    await run(renamer, "custom")
    await run(renamer, "custom")

    renamer.client.client.torrents_rename_file.assert_not_called()
    renamer.client.client.add_tag.assert_not_called()
    assert published(plugins.bus, TorrentOrganized) == []
    events = [e for e in renamer.events if isinstance(e, RenameSkippedEvent)]
    assert len(events) == 1
    assert events[0].task_id == "h1" and events[0].strategy == "custom"
    assert plugins.tripped == (["ext"] if counted else [])


def _task(file_count: int = 1, revision: int | None = 1) -> RevisionTask:
    identity = (
        None
        if revision is None
        else Revision(7, "episode", 1, 1, "ani", "1080p", revision)
    )
    return RevisionTask("h", "name", file_count, identity)


@pytest.mark.parametrize(
    ("owners", "incoming", "configured", "strict", "action", "reason"),
    [
        (
            (_task(), _task()),
            _task(),
            "replace",
            True,
            "hold",
            "canonical path has more than one downloader owner",
        ),
        (
            (_task(file_count=2),),
            _task(),
            "replace",
            True,
            "hold",
            "automatic replacement requires two single-file torrents",
        ),
        (
            (_task(revision=None),),
            _task(),
            "replace",
            True,
            "hold",
            "revision identity is incomplete",
        ),
        (
            (_task(),),
            _task(),
            "replace",
            False,
            "hold",
            "existing and incoming releases are not a strict revision upgrade",
        ),
        ((_task(),), _task(), "hold", True, "hold", "revision conflict policy is hold"),
        ((_task(),), _task(), "replace", True, "replace", ""),
    ],
)
def test_core_conflict_policy_decide_matches_3x_reasons(
    owners, incoming, configured, strict, action, reason
):
    decision = CoreConflictPolicy(configured).decide(
        ConflictRequest("t.mkv", incoming, owners, strict)
    )
    assert (decision.action, decision.reason) == (action, reason)


# ---------------------------------------------------------------- built-in plugin


def load_rename_plugin():
    candidates, errors = discover(
        local_root=BUILTIN_ROOT / "__missing__", entry_point_group="ab-test-none"
    )
    assert errors == []
    return {c.manifest.id: c for c in candidates}["rename"]


def template_strategy(tmp_path, template: str):
    plugin, _ = create_plugin(
        load_rename_plugin().load(), {"template": template}, data_dir=tmp_path
    )
    return plugin.template_strategy()


def rename_input(**overrides) -> RenameInput:
    fields = {
        "kind": "media",
        "media_path": NAME,
        "title": "Anime",
        "bangumi_name": "Anime (2024)",
        "season": 1,
        "episode": 1,
        "suffix": ".mkv",
        "group": "Sub",
    }
    return RenameInput(**{**fields, **overrides})


@pytest.mark.parametrize(
    ("template", "overrides", "expected"),
    [
        (None, {}, "Anime S01E01.mkv"),
        (None, {"episode": 12.5}, "Anime S01E12.5.mkv"),
        (
            "{{ title }} - S{{ season|pad(2) }}E{{ episode|pad(3) }}",
            {"kind": "subtitle", "language": "zh-tw", "suffix": ".ass"},
            "Anime - S01E001.zh-tw.ass",
        ),
        (
            "{% if episode_type == 'movie' %}{{ bangumi_name }}"
            "{% else %}[{{ group }}] {{ title }} {{ episode }}{% endif %}",
            {"episode_type": "movie"},
            "Anime (2024).mkv",
        ),
    ],
)
def test_template_strategy_renders_stem_and_appends_suffix(
    tmp_path, template, overrides, expected
):
    plugin, _ = create_plugin(
        load_rename_plugin().load(),
        {} if template is None else {"template": template},
        data_dir=tmp_path,
    )
    strategy = plugin.template_strategy()
    assert strategy.target_name(rename_input(**overrides)) == expected


@pytest.mark.parametrize(
    "template",
    [
        "{{ title ",  # 语法错误
        "{{ titel }}",  # 未定义变量
        "{{ title.__class__ }}",  # 沙箱拒绝
        "{{ group }}/{{ title }}",  # 路径分隔符
        "{{ '' }}",  # 空文件名
        "..",
    ],
)
def test_template_options_invalid_template_rejected(template):
    options_model = load_rename_plugin().load().config_model
    with pytest.raises(ValidationError):
        options_model.model_validate({"template": template})


@pytest.mark.parametrize(
    ("template", "overrides"),
    [
        ("{{ group }}", {"group": None}),  # 运行时渲染为空
        ("{{ title }}", {"title": "a/b"}),  # 运行时出现分隔符
        ("{{ (episode / season)|int }}", {"season": 0}),  # 运行时渲染异常
    ],
)
def test_template_strategy_bad_runtime_name_raises_skipped(
    tmp_path, template, overrides
):
    strategy = template_strategy(tmp_path, template)
    with pytest.raises(RenameSkipped):
        strategy.target_name(rename_input(**overrides))


async def test_rename_plugin_loaded_by_manager_enabled_by_default(plugins, tmp_path):
    manager = PluginManager(
        SimpleNamespace(plugins=Plugins()),
        registry=plugins.registry,
        discover_fn=lambda: ([load_rename_plugin()], []),
        data_root=tmp_path,
    )
    await manager.start()
    try:
        status = {s.id: s for s in manager.statuses()}["rename"]
        assert status.state == "active"
        strategies = plugins.registry.providers(points.RENAME_STRATEGY)
        assert {pid: e.plugin_id for pid, e in strategies.items()} == {
            "none": "core",
            "pn": "rename",
            "advance": "rename",
            "template": "rename",
        }
        with pytest.raises(ValidationError):
            manager.validate_options("rename", {"template": "{{ nope }}"})
    finally:
        await manager.stop()
    assert set(plugins.registry.providers(points.RENAME_STRATEGY)) == {"none"}
