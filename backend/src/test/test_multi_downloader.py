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
