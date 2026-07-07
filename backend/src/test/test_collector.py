"""Tests for SeasonCollector: torrents must be persisted with bangumi_id.

Regression tests for the orphan-torrent bug: torrents added via
subscribe/collect were stored with ``bangumi_id=None`` and showed up as
orphans regardless of the ``track_orphans`` setting.
"""

from unittest.mock import AsyncMock, patch

from module.database import Database
from module.downloader import AddResult
from module.manager.collector import SeasonCollector
from module.models import Torrent
from test.factories import make_bangumi


def _async_ctx(inner):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _req_with_torrents(torrents):
    req = AsyncMock()
    req.get_torrents = AsyncMock(return_value=torrents)
    return _async_ctx(req)


def _make_torrents():
    return [
        Torrent(
            name="[TestGroup] Test Anime Raw - 01 [1080p].mkv",
            url="https://example.com/ep1.torrent",
        ),
        Torrent(
            name="[TestGroup] Test Anime Raw - 02 [1080p].mkv",
            url="https://example.com/ep2.torrent",
        ),
    ]


class TestCollectSeason:
    async def test_torrents_persisted_with_bangumi_id(self):
        bangumi = make_bangumi(filter="")
        torrents = _make_torrents()
        client = AsyncMock()
        client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
        collector = SeasonCollector(client)

        with patch(
            "module.manager.collector.RequestContent",
            return_value=_req_with_torrents(torrents),
        ):
            resp = await collector.collect_season(bangumi, "https://example.com/rss")

        assert resp.status is True
        async with Database() as db:
            stored = await db.torrent.search_all()
            assert len(stored) == 2
            assert all(t.bangumi_id == bangumi.id for t in stored)
            assert await db.torrent.count_orphans() == 0

    async def test_add_torrent_called_with_persisted_bangumi(self):
        """add_torrent 打 ab:<id> 标签依赖调用时 bangumi.id 已存在。"""
        bangumi = make_bangumi(filter="")
        client = AsyncMock()
        client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
        collector = SeasonCollector(client)

        with patch(
            "module.manager.collector.RequestContent",
            return_value=_req_with_torrents(_make_torrents()),
        ):
            await collector.collect_season(bangumi, "https://example.com/rss")

        passed_bangumi = client.add_torrent.call_args.args[1]
        assert passed_bangumi.id is not None


class TestSubscribeSeason:
    async def test_torrents_persisted_with_bangumi_id(self):
        data = make_bangumi(filter="")
        torrents = _make_torrents()

        downloader_client = AsyncMock()
        downloader_client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
        with (
            patch(
                "module.rss.engine.RequestContent",
                return_value=_req_with_torrents(torrents),
            ),
            patch(
                "module.rss.engine.DownloadClient",
                return_value=_async_ctx(downloader_client),
            ),
        ):
            result = await SeasonCollector.subscribe_season(data)

        assert result.status is True
        assert data.id is not None
        async with Database() as db:
            stored = await db.torrent.search_all()
            assert len(stored) == 2
            assert all(t.bangumi_id == data.id for t in stored)
            assert await db.torrent.count_orphans() == 0
