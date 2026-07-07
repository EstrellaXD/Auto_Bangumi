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

    async def test_duplicate_resolution_preserves_existing_row_fields(self):
        """解析到已存在行时不能用刚解析的默认值覆盖用户调好的配置。"""
        existing = make_bangumi(filter="", episode_offset=12)
        async with Database() as db:
            assert await db.bangumi.add(existing)

        payload = make_bangumi(filter="", episode_offset=0)  # 同 key，默认 offset
        client = AsyncMock()
        client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
        collector = SeasonCollector(client)
        with patch(
            "module.manager.collector.RequestContent",
            return_value=_req_with_torrents(_make_torrents()),
        ):
            resp = await collector.collect_season(payload, "https://example.com/rss")

        assert resp.status is True
        async with Database() as db:
            row = await db.bangumi.search_id(existing.id)
            assert row is not None
            assert row.episode_offset == 12
            assert row.eps_collect is True

    async def test_failed_collect_leaves_no_phantom_bangumi(self):
        """下载器投递失败时不能留下幽灵订阅规则。"""
        bangumi = make_bangumi(filter="")
        client = AsyncMock()
        client.add_torrent = AsyncMock(return_value=AddResult.FAILED)
        collector = SeasonCollector(client)
        with patch(
            "module.manager.collector.RequestContent",
            return_value=_req_with_torrents(_make_torrents()),
        ):
            resp = await collector.collect_season(bangumi, "https://example.com/rss")

        assert resp.status is False
        async with Database() as db:
            assert await db.bangumi.search_all() == []

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
    async def test_existing_bangumi_links_torrents_to_existing_id(self):
        """重复订阅已存在的番剧（add 返回 False）时，种子必须挂到
        已存在行的 id 上，不能被记成孤儿。"""
        existing = make_bangumi(filter="")
        async with Database() as db:
            assert await db.bangumi.add(existing)

        data = make_bangumi(filter="")  # 同 title_raw+group_name -> 精确重复
        downloader_client = AsyncMock()
        downloader_client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
        with (
            patch(
                "module.rss.engine.RequestContent",
                return_value=_req_with_torrents(_make_torrents()),
            ),
            patch(
                "module.rss.engine.DownloadClient",
                return_value=_async_ctx(downloader_client),
            ),
        ):
            result = await SeasonCollector.subscribe_season(data)

        assert result.status is True
        async with Database() as db:
            stored = await db.torrent.search_all()
            assert len(stored) == 2
            assert all(t.bangumi_id == existing.id for t in stored)
            assert await db.torrent.count_orphans() == 0

    async def test_deleted_duplicate_is_not_linked(self):
        """已被软删除（禁用）的重复规则对下游查询不可见——不能把新种子挂上去。"""
        existing = make_bangumi(filter="", deleted=True)
        async with Database() as db:
            assert await db.bangumi.add(existing)

        data = make_bangumi(filter="")
        downloader_client = AsyncMock()
        downloader_client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
        with (
            patch(
                "module.rss.engine.RequestContent",
                return_value=_req_with_torrents(_make_torrents()),
            ),
            patch(
                "module.rss.engine.DownloadClient",
                return_value=_async_ctx(downloader_client),
            ),
        ):
            await SeasonCollector.subscribe_season(data)

        async with Database() as db:
            stored = await db.torrent.search_all()
            assert all(t.bangumi_id != existing.id for t in stored)

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
