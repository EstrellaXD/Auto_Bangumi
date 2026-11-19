"""强制准入不依赖普通过滤的 fail-open 策略，也不依赖 qB 标签。"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ab_sdk import points
from ab_sdk.admission import Admission
from ab_sdk.downloader import AddResult
from module.conf import settings
from module.database import Database
from module.models import Bangumi, Torrent
from module.plugin import host
from module.plugin.admission import (
    HostAdmissionService,
    before_send,
    candidate_batch,
    policy_revision,
)
from module.plugin.registry import ProviderEntry
from module.plugin.runner import CircuitBreaker, HookRunner


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setattr(host, "_registry", None)
    registry = host.get_registry()
    monkeypatch.setattr(host, "_runner", HookRunner(registry, CircuitBreaker()))
    monkeypatch.setattr(settings.plugins.slots, "download_preflight", "review/gate")
    return registry


async def sample():
    async with Database() as db:
        bangumi = Bangumi(
            official_title="Example", title_raw="Example", year="2024", filter=""
        )
        db.add(bangumi)
        await db.commit()
    torrent = Torrent(
        name="[Group] Example - 01", url="magnet:?xt=urn:btih:" + "a" * 40
    )
    return bangumi, torrent


def fake_client(result=AddResult.ADDED, *, timeout=False):
    async def direct(torrents, bangumi):
        torrent = torrents[0] if isinstance(torrents, list) else torrents
        callback = before_send.get()
        assert callback is not None
        await callback(torrent.url, None)
        if timeout:
            return AddResult.FAILED  # 原下载门面将网络异常转换成 FAILED。
        return result

    return SimpleNamespace(
        instance_id="default",
        instance=SimpleNamespace(type="qbittorrent"),
        _add_torrent_direct=AsyncMock(side_effect=direct),
    )


@pytest.mark.parametrize("decision", ["hold", "reject"])
async def test_held_and_rejected_do_not_call_downloader(registry, decision):
    registry.add_provider(
        points.DOWNLOAD_PREFLIGHT,
        ProviderEntry(
            "review",
            "gate",
            lambda: SimpleNamespace(
                preflight=AsyncMock(
                    return_value=Admission(decision, "Choose a version")
                )
            ),
        ),
    )
    bangumi, torrent = await sample()
    client = fake_client()
    assert (
        await HostAdmissionService().submit_with_client(client, torrent, bangumi)
        is AddResult.HELD
    )
    client._add_torrent_direct.assert_not_awaited()


async def test_missing_disabled_and_crashed_required_provider_stay_closed(registry):
    bangumi, torrent = await sample()
    client = fake_client()
    service = HostAdmissionService()
    assert await service.submit_with_client(client, torrent, bangumi) is AddResult.HELD
    registry.add_provider(
        points.DOWNLOAD_PREFLIGHT,
        ProviderEntry(
            "review",
            "gate",
            lambda: SimpleNamespace(
                preflight=AsyncMock(side_effect=RuntimeError("bad plugin"))
            ),
        ),
    )
    assert await service.submit_with_client(client, torrent, bangumi) is AddResult.HELD
    registry.remove_plugin("review")
    assert await service.submit_with_client(client, torrent, bangumi) is AddResult.HELD
    client._add_torrent_direct.assert_not_awaited()


async def test_concurrent_duplicate_and_restart_submit_only_once(registry):
    registry.add_provider(
        points.DOWNLOAD_PREFLIGHT,
        ProviderEntry(
            "review",
            "gate",
            lambda: SimpleNamespace(
                preflight=AsyncMock(return_value=Admission("allow"))
            ),
        ),
    )
    bangumi, torrent = await sample()
    client = fake_client()
    result = await asyncio.gather(
        *(
            HostAdmissionService().submit_with_client(client, torrent, bangumi)
            for _ in range(2)
        )
    )
    assert set(result) == {AddResult.ADDED, AddResult.DUPLICATE}
    assert (
        await HostAdmissionService().submit_with_client(client, torrent, bangumi)
        is AddResult.DUPLICATE
    )
    assert client._add_torrent_direct.await_count == 1


async def test_unknown_outcome_is_not_retried_even_when_task_not_yet_visible(
    registry, monkeypatch
):
    registry.add_provider(
        points.DOWNLOAD_PREFLIGHT,
        ProviderEntry(
            "review",
            "gate",
            lambda: SimpleNamespace(
                preflight=AsyncMock(return_value=Admission("allow"))
            ),
        ),
    )
    bangumi, torrent = await sample()
    client = fake_client(timeout=True)
    service = HostAdmissionService()
    assert (
        await service.submit_with_client(client, torrent, bangumi) is AddResult.FAILED
    )
    from module.downloader import DownloadClient

    monkeypatch.setattr(
        DownloadClient,
        "__aenter__",
        AsyncMock(
            return_value=SimpleNamespace(torrent_exists=AsyncMock(return_value=False))
        ),
    )
    monkeypatch.setattr(DownloadClient, "__aexit__", AsyncMock())
    assert await service.submit_with_client(client, torrent, bangumi) is AddResult.HELD
    assert client._add_torrent_direct.await_count == 1


async def test_candidate_batch_contains_later_revision_before_first_admission(registry):
    bangumi, v1 = await sample()
    v2 = Torrent(name="[Group] Example - 01v2", url="magnet:?xt=urn:btih:" + "b" * 40)
    service = HostAdmissionService()
    with candidate_batch() as batch_id:
        await service.capture(
            [v1, v2], source="rss", bangumi_id=bangumi.id, stage="matched"
        )
        seen = await service.candidates(batch_id=batch_id)
        assert {c.torrent.name for c in seen.items} == {v1.name, v2.name}
        stored = seen.items[0]
    monkey_policy = policy_revision()
    assert monkey_policy
    with pytest.raises(ValueError, match="expired"):
        await service.replay(
            stored.id,
            candidate_revision="old",
            mapping_revision="old",
            idempotency_key="replay",
            policy_revision=monkey_policy,
        )


async def test_replay_preserves_original_batch_and_records_sdk_history(
    registry, monkeypatch
):
    from sqlmodel import select

    from ab_sdk.admission import Submission
    from module.downloader import DownloadClient
    from module.plugin.downloads import HostBangumiService

    bangumi, v1 = await sample()
    v2 = Torrent(
        name="[Group] Example - 01v2 [1080p].mkv", url="magnet:?xt=urn:btih:" + "b" * 40
    )
    service = HostAdmissionService("review")
    seen = []

    async def gate(request):
        page = await service.candidates(batch_id=request.candidates[0].batch_id)
        seen.append({c.torrent.url for c in page.items})
        return Admission("allow")

    registry.add_provider(
        points.DOWNLOAD_PREFLIGHT,
        ProviderEntry("review", "gate", lambda: SimpleNamespace(preflight=gate)),
    )
    with candidate_batch() as batch_id:
        await service.capture([v1, v2], source="rss")
    await service.recheck_candidates(batch_id=batch_id)
    page = await service.candidates(batch_id=batch_id)
    candidate = next(c for c in page.items if c.torrent.url == v2.url)
    assert candidate.release is not None and candidate.release.version == 2
    assert candidate.matched_bangumi_ids == (bangumi.id,)
    client = fake_client()
    client.add_torrent = lambda torrents, owner: service.submit_with_client(
        client, torrents, owner
    )
    monkeypatch.setattr(DownloadClient, "__aenter__", AsyncMock(return_value=client))
    monkeypatch.setattr(DownloadClient, "__aexit__", AsyncMock())
    snapshot = await HostBangumiService().get(bangumi.id)
    assert snapshot is not None
    result = await service.replay(
        candidate.id,
        candidate_revision=candidate.revision,
        mapping_revision=snapshot.revision,
        idempotency_key="pick-v2",
        policy_revision=policy_revision(),
    )
    assert isinstance(result, Submission) and result.state == "accepted"
    assert result.download_ids
    assert seen == [{v1.url, v2.url}]
    async with Database() as db:
        rows = list((await db.session.execute(select(Torrent))).scalars())
    assert len(rows) == 1 and rows[0].url == v2.url and rows[0].downloaded
    assert (await service.lookup_submission("pick-v2")).state == "accepted"
    async with Database() as db:
        assert len(list((await db.session.execute(select(Torrent))).scalars())) == 1


async def test_mapping_change_while_gate_runs_never_sends(registry):
    bangumi, torrent = await sample()

    async def gate(request):
        async with Database() as db:
            current = await db.bangumi.search_id(bangumi.id)
            current.episode_offset = -12
            await db.bangumi.update(current)
        return Admission("allow")

    registry.add_provider(
        points.DOWNLOAD_PREFLIGHT,
        ProviderEntry("review", "gate", lambda: SimpleNamespace(preflight=gate)),
    )
    client = fake_client()
    assert (
        await HostAdmissionService().submit_with_client(client, torrent, bangumi)
        is AddResult.HELD
    )
    client._add_torrent_direct.assert_not_awaited()
