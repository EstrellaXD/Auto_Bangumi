"""多下载器实例（P2.5）：按实例缓存客户端、按规则 / 订阅路由新种子、
重命名逐实例运行、不可用实例跳过并通知一次。两个实例都用 mock 下载器。"""

from unittest.mock import AsyncMock, patch

import pytest

from ab_sdk.events import DownloaderUnavailableEvent, TorrentOrganized
from module.conf import settings
from module.database import Database
from module.downloader import (
    DownloadClient,
    DownloaderPool,
    list_torrents,
    resolve_downloader_id,
)
from module.downloader.client.mock_downloader import MockDownloader
from module.manager import renamer as renamer_module
from module.manager.renamer import Renamer, rename_all
from module.models import Torrent
from module.models.config import PluginInstance, Plugins, Slots
from module.rss.engine import RSSEngine
from test.factories import make_bangumi, make_rss_item


def _instance(instance_id: str, path: str) -> PluginInstance:
    return PluginInstance(
        id=instance_id,
        point="downloader",
        provider="mock",
        options={"host": f"{instance_id}:8080", "path": path},
    )


@pytest.fixture
def two_instances(monkeypatch):
    """实例 a（默认）与 b，各自的下载目录不同。"""
    plugins = Plugins(
        instances=[_instance("a", "/a/Bangumi"), _instance("b", "/b/Bangumi")],
        slots=Slots(downloader="a"),
    )
    monkeypatch.setattr(settings, "plugins", plugins)
    monkeypatch.setattr(renamer_module, "_unavailable", set())
    return plugins


def _mock(instance_id: str) -> MockDownloader:
    client = DownloadClient(instance_id).client
    assert isinstance(client, MockDownloader)
    return client


def _completed(name: str, torrent_hash: str, save_path: str) -> dict:
    return {
        "hash": torrent_hash,
        "name": name,
        "save_path": save_path,
        "category": "Bangumi",
        "state": "completed",
        "progress": 1.0,
        "files": [{"name": f"{name}.mkv", "size": 100}],
        "tags": "",
    }


def test_download_client_qb_and_aria2_side_by_side(monkeypatch):
    """qB 与 aria2 实例并存：各自的后端、地址与版本替换事务命名空间。"""
    from module.downloader.client.aria2_downloader import Aria2Downloader
    from module.downloader.client.qb_downloader import QbDownloader

    plugins = Plugins(
        instances=[
            PluginInstance(
                id="qb",
                point="downloader",
                provider="qbittorrent",
                options={"host": "qb:8080"},
            ),
            PluginInstance(
                id="ar",
                point="downloader",
                provider="aria2",
                options={"host": "ar:6800"},
            ),
        ],
        slots=Slots(downloader="qb"),
    )
    monkeypatch.setattr(settings, "plugins", plugins)
    qb, ar = DownloadClient("qb"), DownloadClient("ar")
    assert isinstance(qb.client, QbDownloader)
    assert isinstance(ar.client, Aria2Downloader)
    assert ar.client.host.endswith("ar:6800")
    assert ar.client.instance_id == "ar"
    assert Renamer(qb)._downloader_type() != Renamer(ar)._downloader_type()


class TestClientCache:
    def test_download_client_two_instances_separate_cached_clients(self, two_instances):
        a, b = _mock("a"), _mock("b")
        assert a is not b
        assert _mock("a") is a
        assert DownloadClient().instance_id == "a"

    async def test_download_client_credentials_rejected_latch_is_per_instance(
        self, two_instances
    ):
        b = _mock("b")
        b.auth = AsyncMock(return_value=False)  # type: ignore[method-assign]
        b.last_auth_error = "credentials"  # type: ignore[attr-defined]
        with pytest.raises(ConnectionError):
            async with DownloadClient("b"):
                pass
        with pytest.raises(ConnectionError):
            async with DownloadClient("b"):
                pass
        assert b.auth.await_count == 1  # 闩锁命中，不再登录
        async with DownloadClient("a") as client:
            assert client.authed


@pytest.mark.parametrize(
    "candidates, expected",
    [
        ((None, None), "a"),
        (("", None), "a"),
        (("b", None), "b"),
        ((None, "b"), "b"),
        (("a", "b"), "a"),
        (("gone", "b"), "b"),
        (("gone",), "a"),
    ],
)
def test_resolve_downloader_id_candidates_first_known_else_default(
    two_instances, candidates, expected
):
    assert resolve_downloader_id(*candidates) == expected


class TestRssRouting:
    @pytest.mark.parametrize(
        "bangumi_instance, rss_instance, expected",
        [("b", None, "b"), (None, "b", "b"), (None, None, "a"), ("a", "b", "a")],
    )
    async def test_refresh_rss_adds_to_rule_then_feed_then_default_instance(
        self, two_instances, db_engine, bangumi_instance, rss_instance, expected
    ):
        engine = RSSEngine(Database(engine=db_engine))
        await engine.db.rss.add(make_rss_item(enabled=True, downloader_id=rss_instance))
        await engine.db.bangumi.add(
            make_bangumi(
                title_raw="Mushoku Tensei",
                filter="",
                save_path=None,
                downloader_id=bangumi_instance,
            )
        )
        torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="magnet:?xt=urn:btih:12",
        )
        with patch.object(
            RSSEngine, "_get_torrents", AsyncMock(return_value=[torrent])
        ):
            async with DownloaderPool() as pool:
                await engine.refresh_rss(pool)

        rows = await engine.db.torrent.search_all()
        assert [(r.downloaded, r.downloader_id) for r in rows] == [(True, expected)]
        other = "a" if expected == "b" else "b"
        assert len(_mock(expected)._torrents) == 1
        assert _mock(other)._torrents == {}
        # 新规则的保存目录取目标实例的下载目录
        (added,) = _mock(expected)._torrents.values()
        assert added["save_path"].startswith(f"/{expected}/Bangumi/")

    @pytest.mark.parametrize(
        "default, bangumi_instance, rss_instance",
        [("b", None, None), ("b", "gone", None), ("a", None, "b")],
    )
    async def test_refresh_rss_save_path_of_other_instance_rerooted(
        self,
        two_instances,
        db_engine,
        monkeypatch,
        default,
        bangumi_instance,
        rss_instance,
    ):
        """默认实例切换、规则的实例被删除、订阅指向另一实例：已存的保存目录
        属于实例 a，新种子进实例 b 时必须换成 b 的下载目录。"""
        monkeypatch.setattr(two_instances.slots, "downloader", default)
        engine = RSSEngine(Database(engine=db_engine))
        await engine.db.rss.add(make_rss_item(enabled=True, downloader_id=rss_instance))
        await engine.db.bangumi.add(
            make_bangumi(
                title_raw="Mushoku Tensei",
                filter="",
                save_path="/a/Bangumi/Test Anime (2024)/Season 1",
                downloader_id=bangumi_instance,
            )
        )
        torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="magnet:?xt=urn:btih:12",
        )
        with patch.object(
            RSSEngine, "_get_torrents", AsyncMock(return_value=[torrent])
        ):
            async with DownloaderPool() as pool:
                await engine.refresh_rss(pool)

        (added,) = _mock("b")._torrents.values()
        assert added["save_path"] == "/b/Bangumi/Test Anime (2024)/Season 1"
        (rule,) = await engine.db.bangumi.search_all()
        assert rule.save_path == "/b/Bangumi/Test Anime (2024)/Season 1"

    async def test_refresh_rss_unavailable_instance_torrent_not_persisted(
        self, two_instances, db_engine
    ):
        engine = RSSEngine(Database(engine=db_engine))
        await engine.db.rss.add(make_rss_item(enabled=True))
        await engine.db.bangumi.add(
            make_bangumi(title_raw="Mushoku Tensei", filter="", downloader_id="b")
        )
        _mock("b").auth = AsyncMock(return_value=False)  # type: ignore[method-assign]
        torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="magnet:?xt=urn:btih:12",
        )
        with patch.object(
            RSSEngine, "_get_torrents", AsyncMock(return_value=[torrent])
        ):
            async with DownloaderPool() as pool:
                events = await engine.refresh_rss(pool)

        assert events == []
        assert await engine.db.torrent.search_all() == []  # 下一轮重试


class TestRenameAll:
    async def test_rename_all_events_carry_instance_of_torrent(self, two_instances):
        _mock("b")._torrents["hb"] = _completed(
            "[Sub] Show - 01 [1080p]", "hb", "/b/Bangumi/Show/Season 1"
        )
        published: list[object] = []
        with patch.object(renamer_module.plugin_host, "publish", published.append):
            renamed, events = await rename_all()

        organized = [e for e in published if isinstance(e, TorrentOrganized)]
        assert [(e.torrent_hash, e.downloader_id) for e in organized] == [("hb", "b")]
        assert events == []
        assert [n.official_title for n in renamed] == ["Show"]

    async def test_rename_all_unavailable_instance_skipped_and_notified_once(
        self, two_instances
    ):
        _mock("a")._torrents["ha"] = _completed(
            "[Sub] Show - 01 [1080p]", "ha", "/a/Bangumi/Show/Season 1"
        )
        _mock("b").auth = AsyncMock(return_value=False)  # type: ignore[method-assign]

        first_renamed, first_events = await rename_all()
        _, second_events = await rename_all()

        assert [n.official_title for n in first_renamed] == ["Show"]
        assert first_events == [
            DownloaderUnavailableEvent(
                host="b:8080", reason="unreachable", instance_id="b"
            )
        ]
        assert second_events == []

    async def test_rename_all_recovered_instance_notified_again_on_next_outage(
        self, two_instances
    ):
        counts = []
        for reachable in (False, True, False):
            # 登录失败后缓存的客户端被丢弃，每轮给新取到的客户端打桩
            _mock("b").auth = AsyncMock(return_value=reachable)  # type: ignore[method-assign]
            counts.append(len((await rename_all())[1]))
        assert counts == [1, 0, 1]

    async def test_rename_replacement_of_other_instance_not_recovered(
        self, two_instances
    ):
        """实例 a 的版本替换事务不能被实例 b 的重命名当成「新种子已消失」去恢复。"""
        from module.models.rename_operation import RenameOperation

        async with DownloadClient("a") as client_a:
            a_type = Renamer(client_a)._downloader_type()
        async with Database() as db:
            db.add(
                RenameOperation(
                    kind="replacement",
                    state="planned",
                    downloader_type=a_type,
                    new_task_id="only-on-a",
                    save_path="/a/Bangumi/Show/Season 1",
                    target_path="Show S01E01.mkv",
                    source_path="x.mkv",
                )
            )
            await db.commit()

        with patch.object(
            Renamer, "_recover_missing_replacement", AsyncMock()
        ) as recover:
            async with DownloadClient("b") as client_b:
                await Renamer(client_b).rename()
        recover.assert_not_awaited()


async def test_rename_single_instance_replacement_after_host_change_recovered(
    monkeypatch,
):
    """只有一个实例时，改了主机地址（同一个 qB）后仍要恢复进行中的版本替换。"""
    from module.models.rename_operation import RenameOperation

    monkeypatch.setattr(
        settings,
        "plugins",
        Plugins(instances=[_instance("a", "/a/Bangumi")], slots=Slots(downloader="a")),
    )
    async with Database() as db:
        db.add(
            RenameOperation(
                kind="replacement",
                state="old_staged",
                downloader_type="mock:old-host-hash",
                new_task_id="gone",
                save_path="/a/Bangumi/Show/Season 1",
                target_path="Show S01E01.mkv",
                source_path="x.mkv",
            )
        )
        await db.commit()

    with patch.object(Renamer, "_recover_missing_replacement", AsyncMock()) as recover:
        async with DownloadClient("a") as client:
            await Renamer(client).rename()
    recover.assert_awaited_once()


async def test_list_torrents_one_instance_down_lists_the_other(two_instances):
    _mock("a")._torrents["ha"] = _completed("A", "ha", "/a/Bangumi/A/Season 1")
    _mock("b").auth = AsyncMock(return_value=False)  # type: ignore[method-assign]
    listed = await list_torrents()
    assert [(t["hash"], t["downloader_id"]) for t in listed or []] == [("ha", "a")]


class TestRuleOnAnotherInstance:
    """规则换到另一个实例后，旧种子留在原实例；删除规则时两边的种子都删。"""

    async def _rule_with_torrent_on_a(self) -> int:
        _mock("a")._torrents["old"] = _completed(
            "Old", "old", "/a/Bangumi/Test Anime (2024)/Season 1"
        )
        async with Database() as db:
            await db.bangumi.add(
                make_bangumi(save_path="/a/Bangumi/Test Anime (2024)/Season 1")
            )
            await db.torrent.add(
                Torrent(name="Old", url="u-old", bangumi_id=1, downloader_id="a")
            )
        return 1

    async def test_update_rule_without_downloader_field_keeps_rule_instance(
        self, two_instances
    ):
        """只改其它字段的部分更新（未带 downloader_id）不能把规则改回默认实例。"""
        from module.manager import TorrentManager
        from module.models import BangumiUpdate

        bangumi_id = await self._rule_with_torrent_on_a()
        async with Database() as db:
            bangumi = await db.bangumi.search_id(bangumi_id)
            assert bangumi is not None
            bangumi.downloader_id = "b"
            await db.bangumi.update(bangumi)
            fields = bangumi.model_dump(exclude={"id", "downloader_id"})
            await TorrentManager(db).update_rule(bangumi_id, BangumiUpdate(**fields))
            new = await db.bangumi.search_id(bangumi_id)

        assert new is not None and new.downloader_id == "b"
        assert new.save_path == "/b/Bangumi/Test Anime (2024)/Season 1"

    async def test_update_rule_new_instance_keeps_old_torrents_in_place(
        self, two_instances
    ):
        from module.manager import TorrentManager
        from module.models import BangumiUpdate

        bangumi_id = await self._rule_with_torrent_on_a()
        async with Database() as db:
            old = await db.bangumi.search_id(bangumi_id)
            assert old is not None
            update = BangumiUpdate(**old.model_dump(exclude={"id"}))
            update.downloader_id = "b"
            await TorrentManager(db).update_rule(bangumi_id, update)
            new = await db.bangumi.search_id(bangumi_id)

        assert new is not None and new.downloader_id == "b"
        assert new.save_path == "/b/Bangumi/Test Anime (2024)/Season 1"
        moved = _mock("a")._torrents["old"]["save_path"]
        assert moved == "/a/Bangumi/Test Anime (2024)/Season 1"

    async def test_delete_rule_deletes_torrents_on_every_instance(self, two_instances):
        from module.manager import TorrentManager

        bangumi_id = await self._rule_with_torrent_on_a()
        _mock("b")._torrents["new"] = _completed(
            "New", "new", "/a/Bangumi/Test Anime (2024)/Season 1"
        )
        async with Database() as db:
            bangumi = await db.bangumi.search_id(bangumi_id)
            assert bangumi is not None
            bangumi.downloader_id = "b"
            await db.bangumi.update(bangumi)
            resp = await TorrentManager(db).delete_rule(bangumi_id, file=True)

        assert resp.status
        assert _mock("a")._torrents == {}
        assert _mock("b")._torrents == {}

    async def test_update_rule_moves_torrents_on_instance_of_torrent_rows(
        self, two_instances
    ):
        """规则未指定实例，种子经订阅进了实例 b：改季度要移动 b 上的种子。"""
        from module.manager import TorrentManager
        from module.models import BangumiUpdate

        _mock("b")._torrents["hb"] = _completed(
            "B", "hb", "/b/Bangumi/Test Anime (2024)/Season 1"
        )
        async with Database() as db:
            await db.bangumi.add(
                make_bangumi(save_path="/a/Bangumi/Test Anime (2024)/Season 1")
            )
            await db.torrent.add(
                Torrent(name="B", url="u-b", bangumi_id=1, downloader_id="b")
            )
            old = await db.bangumi.search_id(1)
            assert old is not None
            update = BangumiUpdate(**old.model_dump(exclude={"id"}))
            update.season = 2
            await TorrentManager(db).update_rule(1, update)

        moved = _mock("b")._torrents["hb"]["save_path"]
        assert moved == "/b/Bangumi/Test Anime (2024)/Season 2"

    async def test_update_rule_unavailable_instance_changes_nothing_for_retry(
        self, two_instances
    ):
        """实例 b 不可用：a 上的种子不移动、规则不改，b 恢复后重试两边一起移动。"""
        from module.manager import TorrentManager
        from module.models import BangumiUpdate

        bangumi_id = await self._rule_with_torrent_on_a()
        hb = _completed("B", "hb", "/b/Bangumi/Test Anime (2024)/Season 1")
        _mock("b")._torrents["hb"] = hb
        _mock("b").auth = AsyncMock(return_value=False)  # type: ignore[method-assign]
        async with Database() as db:
            await db.torrent.add(
                Torrent(name="B", url="u-b", bangumi_id=1, downloader_id="b")
            )
            old = await db.bangumi.search_id(bangumi_id)
            assert old is not None
            update = BangumiUpdate(**old.model_dump(exclude={"id"}))
            update.season = 2
            resp = await TorrentManager(db).update_rule(bangumi_id, update)
            assert resp.status is False and resp.status_code == 500
            assert _mock("a")._torrents["old"]["save_path"] == old.save_path
            kept = await db.bangumi.search_id(bangumi_id)
            assert kept is not None and kept.save_path == old.save_path

            # 登录失败会丢弃缓存的客户端，恢复后是新的客户端实例
            _mock("b")._torrents["hb"] = hb
            update = BangumiUpdate(**old.model_dump(exclude={"id"}))
            update.season = 2
            retry = await TorrentManager(db).update_rule(bangumi_id, update)
            assert retry.status is True
            new = await db.bangumi.search_id(bangumi_id)

        season2 = "Bangumi/Test Anime (2024)/Season 2"
        assert new is not None and new.save_path == f"/a/{season2}"
        assert _mock("a")._torrents["old"]["save_path"] == f"/a/{season2}"
        assert _mock("b")._torrents["hb"]["save_path"] == f"/b/{season2}"

    async def test_delete_rule_unavailable_instance_keeps_rule_for_retry(
        self, two_instances
    ):
        """实例 a 不可用：b 上的种子照常删除，规则与种子行保留，a 恢复后重试删净。"""
        from module.manager import TorrentManager

        bangumi_id = await self._rule_with_torrent_on_a()
        _mock("b")._torrents["new"] = _completed(
            "New", "new", "/b/Bangumi/Test Anime (2024)/Season 1"
        )
        auth = _mock("a").auth
        _mock("a").auth = AsyncMock(return_value=False)  # type: ignore[method-assign]
        async with Database() as db:
            await db.torrent.add(
                Torrent(name="New", url="u-new", bangumi_id=1, downloader_id="b")
            )
            resp = await TorrentManager(db).delete_rule(bangumi_id, file=True)
            assert _mock("b")._torrents == {}
            assert resp.status is False and resp.status_code == 500
            assert await db.bangumi.search_id(bangumi_id) is not None
            rows = await db.torrent.search_by_bangumi_id(bangumi_id)
            assert "a" in {r.downloader_id for r in rows}

            _mock("a").auth = auth  # type: ignore[method-assign]
            retry = await TorrentManager(db).delete_rule(bangumi_id, file=True)
            assert retry.status is True
            assert _mock("a")._torrents == {}
            assert await db.bangumi.search_id(bangumi_id) is None
            assert await db.torrent.search_by_bangumi_id(bangumi_id) == []


async def test_eps_complete_unavailable_instance_other_rules_collected(two_instances):
    from module.manager import collector

    async with Database() as db:
        await db.bangumi.add(make_bangumi(official_title="On B", downloader_id="b"))
        await db.bangumi.add(make_bangumi(official_title="On A", title_raw="A raw"))
    _mock("b").auth = AsyncMock(return_value=False)  # type: ignore[method-assign]

    with patch.object(
        collector.SeasonCollector, "collect_season", AsyncMock()
    ) as collect:
        await collector.eps_complete()

    assert [c.args[0].official_title for c in collect.await_args_list] == ["On A"]
    async with Database() as db:
        rules = {b.official_title: b.eps_collect for b in await db.bangumi.search_all()}
    assert rules == {"On B": False, "On A": True}


class TestDownloaderApi:
    def test_pause_routes_to_given_instance(self, two_instances, authed_client):
        _mock("b")._torrents["hb"] = _completed("B", "hb", "/b/Bangumi/B")
        resp = authed_client.post(
            "/api/v1/downloader/torrents/pause",
            json={"hashes": ["hb"], "downloader_id": "b"},
        )
        assert resp.status_code == 200
        assert _mock("b")._torrents["hb"]["state"] == "paused"

    def test_pause_unknown_instance_404(self, two_instances, authed_client):
        resp = authed_client.post(
            "/api/v1/downloader/torrents/pause",
            json={"hashes": ["hb"], "downloader_id": "gone"},
        )
        assert resp.status_code == 404

    def test_instances_lists_downloaders_and_default(
        self, two_instances, authed_client
    ):
        resp = authed_client.get("/api/v1/downloader/instances")
        assert resp.json() == {
            "default": "a",
            "instances": [
                {"id": "a", "provider": "mock"},
                {"id": "b", "provider": "mock"},
            ],
        }

    def test_auto_tag_unavailable_instance_skipped(self, two_instances, authed_client):
        _mock("a")._torrents["ha"] = _completed("A", "ha", "/a/Bangumi/A/Season 1")
        _mock("b").auth = AsyncMock(return_value=False)  # type: ignore[method-assign]
        resp = authed_client.post("/api/v1/downloader/torrents/tag/auto")
        assert resp.status_code == 200
        assert [t["hash"] for t in resp.json()["unmatched"]] == ["ha"]

    def test_add_rss_keeps_downloader_instance(self, two_instances, authed_client):
        resp = authed_client.post(
            "/api/v1/rss/add",
            json={"url": "https://e/rss", "name": "Feed", "downloader_id": "b"},
        )
        assert resp.status_code == 200
        (feed,) = authed_client.get("/api/v1/rss").json()
        assert feed["downloader_id"] == "b"
