"""多下载器列表去重的回归测试；qB 网络响应由测试替身提供。"""

import asyncio
import gc
import warnings

import pytest

from module.conf import settings
from module.database import Database
from module.downloader import list_torrents
from module.downloader.client.qb_downloader import QbDownloader
from module.models import Bangumi, Torrent
from module.models.config import PluginInstance, Plugins, Slots

HASH_A = "0123456789abcdef0123456789abcdef01234567"
HASH_B = "89abcdef0123456789abcdef0123456789abcdef"


def _instance(instance_id, host, path, username=""):
    return PluginInstance(
        id=instance_id,
        point="downloader",
        provider="qbittorrent",
        options={"host": host, "path": path, "username": username},
    )


def _torrent(torrent_hash):
    return {
        "hash": torrent_hash,
        "name": "Episode",
        "save_path": "/downloads/Show",
        "category": "Bangumi",
        "state": "downloading",
        "progress": 0.5,
        "tags": "",
    }


@pytest.fixture
def qb_lists(monkeypatch):
    """保留真实实例配置与列表聚合，仅替换 qB 的外部网络调用。"""
    responses: dict[str, list[dict] | None] = {}

    async def auth(client, retry=3):
        return client.host not in responses or responses[client.host] is not None

    async def torrents_info(client, status_filter, category, tag=None):
        assert status_filter is None
        assert category == "Bangumi"
        return responses[client.host]

    monkeypatch.setattr(QbDownloader, "auth", auth)
    monkeypatch.setattr(QbDownloader, "torrents_info", torrents_info)

    def configure(instances, lists):
        monkeypatch.setattr(
            settings,
            "plugins",
            Plugins(instances=instances, slots=Slots(downloader=instances[0].id)),
        )
        responses.update(lists)

    return configure


def _listed_keys(listed):
    assert listed is not None
    return [(item["hash"], item["downloader_id"]) for item in listed]


async def test_cancelling_list_before_children_start_does_not_leak_coroutines(qb_lists):
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        task = asyncio.create_task(list_torrents(timeout=5))
        # list_torrents runs first and schedules its children; cancellation
        # then arrives before those children get a chance to start.
        asyncio.get_running_loop().call_soon(task.cancel)
        with pytest.raises(asyncio.CancelledError):
            await task
        del task
        gc.collect()
        await asyncio.sleep(0)
        gc.collect()

    leaked = [
        str(w.message)
        for w in caught
        if issubclass(w.category, RuntimeWarning)
        and "was never awaited" in str(w.message)
    ]
    assert leaked == []


async def test_duplicate_hash_from_one_instance_is_listed_once(qb_lists):
    qb_lists(
        [_instance("a", "qb:8080", "/a")],
        {"http://qb:8080": [_torrent(HASH_A), _torrent(HASH_A)]},
    )

    assert _listed_keys(await list_torrents()) == [(HASH_A, "a")]


async def test_same_hash_on_independent_qb_services_remains_visible(qb_lists):
    qb_lists(
        [_instance("a", "qb-a:8080", "/a"), _instance("b", "qb-b:8080", "/b")],
        {
            "http://qb-a:8080": [_torrent(HASH_A)],
            "http://qb-b:8080": [_torrent(HASH_A)],
        },
    )
    assert _listed_keys(await list_torrents()) == [(HASH_A, "a"), (HASH_A, "b")]


async def test_same_qb_different_hashes_are_each_visible_once(qb_lists):
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A), _torrent(HASH_B)]},
    )
    assert _listed_keys(await list_torrents()) == [(HASH_A, "a"), (HASH_B, "a")]


async def test_known_torrent_owner_is_preferred_for_same_qb(qb_lists):
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )
    async with Database() as db:
        await db.torrent.add(Torrent(name="Episode", qb_hash=HASH_A, downloader_id="b"))

    assert _listed_keys(await list_torrents()) == [(HASH_A, "b")]


async def test_bangumi_current_downloader_is_preferred_from_qb_tag(qb_lists):
    torrent = _torrent(HASH_A)
    torrent["tags"] = "ab:7"
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [torrent]},
    )
    async with Database() as db:
        db.add(
            Bangumi(
                id=7,
                official_title="Show",
                title_raw="Show",
                downloader_id="b",
            )
        )
        db.add(
            Torrent(
                name="Episode",
                refer_id=7,
                qb_hash=HASH_A,
                downloader_id="a",
                downloaded=True,
            )
        )
        await db.commit()

    assert _listed_keys(await list_torrents()) == [(HASH_A, "b")]


async def test_bangumi_tag_uses_unique_downloaded_owner_when_current_owner_is_unset(
    qb_lists,
):
    torrent = _torrent(HASH_A)
    torrent["tags"] = "ab:8"
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [torrent]},
    )
    async with Database() as db:
        db.add(Bangumi(id=8, official_title="Show", title_raw="Show"))
        db.add(
            Torrent(
                name="Episode",
                refer_id=8,
                downloader_id="b",
                downloaded=True,
            )
        )
        await db.commit()

    assert _listed_keys(await list_torrents()) == [(HASH_A, "b")]


@pytest.mark.parametrize(
    "tags",
    [
        "",
        "ab:renamed",
        "ab:999",
        "ab:1,ab:2",
        pytest.param("ab:" + "7" * 5000, id="oversized-numeric-tag"),
    ],
)
async def test_missing_or_ambiguous_bangumi_tags_fall_back_to_instance_order(
    qb_lists, tags
):
    torrent = _torrent(HASH_A)
    torrent["tags"] = tags
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [torrent]},
    )

    assert _listed_keys(await list_torrents()) == [(HASH_A, "a")]


async def test_renamed_marker_does_not_make_bangumi_tag_ambiguous(qb_lists):
    torrent = _torrent(HASH_A)
    torrent["tags"] = "ab:7, ab:renamed"
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [torrent]},
    )
    async with Database() as db:
        db.add(
            Bangumi(id=7, official_title="Show", title_raw="Show", downloader_id="b")
        )
        await db.commit()

    assert _listed_keys(await list_torrents()) == [(HASH_A, "b")]


async def test_unknown_ab_tag_keeps_bangumi_association_ambiguous(qb_lists):
    torrent = _torrent(HASH_A)
    torrent["tags"] = "ab:7, ab:legacy"
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [torrent]},
    )
    async with Database() as db:
        db.add(
            Bangumi(id=7, official_title="Show", title_raw="Show", downloader_id="b")
        )
        await db.commit()

    assert _listed_keys(await list_torrents()) == [(HASH_A, "a")]


async def test_owner_lookup_matches_hashes_case_insensitively(qb_lists):
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )
    async with Database() as db:
        await db.torrent.add(
            Torrent(name="Episode", qb_hash=HASH_A.upper(), downloader_id="b")
        )

    assert _listed_keys(await list_torrents()) == [(HASH_A, "b")]


async def test_owner_does_not_hide_same_hash_on_independent_service(qb_lists):
    qb_lists(
        [
            _instance("a", "qb-a:8080", "/a"),
            _instance("b", "qb-a:8080", "/b"),
            _instance("c", "qb-c:8080", "/c"),
        ],
        {
            "http://qb-a:8080": [_torrent(HASH_A)],
            "http://qb-c:8080": [_torrent(HASH_A)],
        },
    )
    async with Database() as db:
        await db.torrent.add(Torrent(name="Episode", qb_hash=HASH_A, downloader_id="b"))

    assert _listed_keys(await list_torrents()) == [(HASH_A, "b"), (HASH_A, "c")]


async def test_different_credentials_do_not_prove_same_connection(qb_lists):
    qb_lists(
        [
            _instance("a", "qb:8080", "/a", username="alice"),
            _instance("b", "qb:8080", "/b", username="bob"),
        ],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )
    assert _listed_keys(await list_torrents()) == [(HASH_A, "a"), (HASH_A, "b")]


async def test_unreachable_instance_does_not_hide_other_service(qb_lists):
    qb_lists(
        [_instance("a", "down:8080", "/a"), _instance("b", "qb-b:8080", "/b")],
        {"http://down:8080": None, "http://qb-b:8080": [_torrent(HASH_A)]},
    )
    assert _listed_keys(await list_torrents()) == [(HASH_A, "b")]


async def test_single_downloader_keeps_all_torrents(qb_lists):
    qb_lists(
        [_instance("a", "qb:8080", "/a")],
        {"http://qb:8080": [_torrent(HASH_A), _torrent(HASH_B)]},
    )
    assert _listed_keys(await list_torrents()) == [(HASH_A, "a"), (HASH_B, "a")]


async def test_conflicting_owners_fall_back_to_first_successful_instance(qb_lists):
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )
    async with Database() as db:
        await db.torrent.add_all(
            [
                Torrent(name="First", qb_hash=HASH_A, downloader_id="a"),
                Torrent(name="Second", qb_hash=HASH_A, downloader_id="b"),
            ]
        )

    assert _listed_keys(await list_torrents()) == [(HASH_A, "a")]


async def test_database_lookup_failure_still_lists_one_per_same_connection(
    qb_lists, monkeypatch
):
    from module.database.torrent import TorrentDatabase

    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )

    calls = []

    async def fail_lookup(self, hashes):
        calls.append(hashes)
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(TorrentDatabase, "search_by_qb_hashes", fail_lookup)
    assert _listed_keys(await list_torrents()) == [(HASH_A, "a")]
    assert calls == [[HASH_A]]


async def test_database_lookup_timeout_falls_back_to_instance_order(
    qb_lists, monkeypatch
):
    from module.database.torrent import TorrentDatabase

    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )

    calls = []

    async def hang_lookup(self, hashes):
        calls.append(hashes)
        await asyncio.Event().wait()

    monkeypatch.setattr(TorrentDatabase, "search_by_qb_hashes", hang_lookup)
    listed = await asyncio.wait_for(list_torrents(timeout=0.01), timeout=0.5)
    assert _listed_keys(listed) == [(HASH_A, "a")]
    assert calls == [[HASH_A]]


async def test_database_lookup_has_default_timeout(qb_lists, monkeypatch):
    from module.database.torrent import TorrentDatabase

    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )
    monkeypatch.setattr(
        "module.downloader.download_client._OWNER_LOOKUP_TIMEOUT_SECONDS",
        0.01,
        raising=False,
    )

    async def hang_lookup(self, hashes):
        await asyncio.Event().wait()

    monkeypatch.setattr(TorrentDatabase, "search_by_qb_hashes", hang_lookup)
    listed = await asyncio.wait_for(list_torrents(), timeout=0.5)
    assert _listed_keys(listed) == [(HASH_A, "a")]


async def test_missing_hash_is_not_used_for_deduplication(qb_lists):
    torrent = _torrent(HASH_A)
    torrent.pop("hash")
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [torrent]},
    )
    listed = await list_torrents()
    assert listed is not None
    assert [item["downloader_id"] for item in listed] == ["a", "b"]


@pytest.mark.parametrize(
    "operation,method",
    [
        ("pause", "torrents_pause"),
        ("resume", "torrents_resume"),
        ("delete", "torrents_delete"),
    ],
)
def test_deduplicated_torrent_operation_routes_to_selected_connection(
    qb_lists, monkeypatch, authed_client, operation, method
):
    qb_lists(
        [_instance("a", "qb:8080", "/a"), _instance("b", "qb:8080", "/b")],
        {"http://qb:8080": [_torrent(HASH_A)]},
    )
    calls = []

    async def operate(client, hashes, **kwargs):
        calls.append((client.host, hashes, kwargs))
        return True

    monkeypatch.setattr(QbDownloader, method, operate)
    response = authed_client.get("/api/v1/downloader/torrents")
    assert response.status_code == 200
    torrents = response.json()
    assert len(torrents) == 1
    torrent = torrents[0]
    response = authed_client.post(
        f"/api/v1/downloader/torrents/{operation}",
        json={"hashes": [torrent["hash"]], "downloader_id": torrent["downloader_id"]},
    )
    assert response.status_code == 200
    expected_kwargs = {"delete_files": False} if operation == "delete" else {}
    assert calls == [("http://qb:8080", HASH_A, expected_kwargs)]
