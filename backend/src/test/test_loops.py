"""Tests for core/loops.py: notifier wiring for system events.

Covers the new call sites added for non-episode notifications (RSS failure,
download failure, offset review) -- the engine/scanner logic that produces
these events is already covered by test_rss_engine_new.py and
test_offset_scanner.py; these tests exercise the tick-level glue that turns
returned events into ``notifier.send_event`` calls, gated by
``settings.notification.enable``.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from module.core.loops import (
    offset_scan_tick,
    rename_tick,
    rss_tick,
    update_check_tick,
)
from module.models.bangumi import Notification
from module.notification.events import (
    OffsetReviewEvent,
    RssFailureEvent,
    UpdateAvailableEvent,
)

# ---------------------------------------------------------------------------
# offset_scan_tick
# ---------------------------------------------------------------------------


class TestOffsetScanTick:
    async def test_sends_event_per_flagged_bangumi_when_enabled(self):
        """Each event scan_all() returns is forwarded to the notifier."""
        event = OffsetReviewEvent(official_title="Test Anime", reason="mismatch")
        notifier = AsyncMock()

        with patch("module.core.loops.OffsetScanner") as mock_scanner_cls:
            mock_scanner_cls.return_value.scan_all = AsyncMock(return_value=[event])
            with patch("module.core.loops.settings") as mock_settings:
                mock_settings.notification.enable = True
                await offset_scan_tick(notifier)

        notifier.send_event.assert_awaited_once_with(event)

    async def test_events_forwarded_even_when_external_push_disabled(self):
        """事件总是送达 notifier：站内落库不受 enable 开关影响（外发 gating
        在 NotificationManager.send_event 内部）。"""
        event = OffsetReviewEvent(official_title="Test Anime", reason="mismatch")
        notifier = AsyncMock()

        with patch("module.core.loops.OffsetScanner") as mock_scanner_cls:
            mock_scanner_cls.return_value.scan_all = AsyncMock(return_value=[event])
            with patch("module.core.loops.settings") as mock_settings:
                mock_settings.notification.enable = False
                await offset_scan_tick(notifier)

        notifier.send_event.assert_awaited_once_with(event)

    async def test_no_events_flagged_sends_nothing(self):
        """An empty scan result sends no notifications."""
        notifier = AsyncMock()

        with patch("module.core.loops.OffsetScanner") as mock_scanner_cls:
            mock_scanner_cls.return_value.scan_all = AsyncMock(return_value=[])
            with patch("module.core.loops.settings") as mock_settings:
                mock_settings.notification.enable = True
                await offset_scan_tick(notifier)

        notifier.send_event.assert_not_awaited()


# ---------------------------------------------------------------------------
# rss_tick
# ---------------------------------------------------------------------------


def _async_cm(entered_value):
    """Build a mock usable as ``async with X() as y:`` yielding entered_value."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=entered_value)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestRssTick:
    async def test_sends_events_returned_by_refresh_rss(self):
        """Every event refresh_rss() returns is forwarded to the notifier."""
        events = [RssFailureEvent(rss_name="Feed", rss_url="u", error="e")]
        notifier = AsyncMock()
        analyser = AsyncMock()

        mock_db = AsyncMock()
        mock_db.rss.search_aggregate = AsyncMock(return_value=[])
        mock_engine = AsyncMock()
        mock_engine.refresh_rss = AsyncMock(return_value=events)

        with (
            patch(
                "module.core.loops.DownloadClient",
                return_value=_async_cm(AsyncMock()),
            ),
            patch("module.core.loops.Database", return_value=_async_cm(mock_db)),
            patch("module.core.loops.RSSEngine", return_value=mock_engine),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.notification.enable = True
            mock_settings.bangumi_manage.eps_complete = False
            await rss_tick(analyser, notifier)

        notifier.send_event.assert_awaited_once_with(events[0])

    async def test_events_forwarded_even_when_external_push_disabled(self):
        """事件总是送达 notifier（站内落库），外发 gating 在 manager 内部。"""
        events = [RssFailureEvent(rss_name="Feed", rss_url="u", error="e")]
        notifier = AsyncMock()
        analyser = AsyncMock()

        mock_db = AsyncMock()
        mock_db.rss.search_aggregate = AsyncMock(return_value=[])
        mock_engine = AsyncMock()
        mock_engine.refresh_rss = AsyncMock(return_value=events)

        with (
            patch(
                "module.core.loops.DownloadClient",
                return_value=_async_cm(AsyncMock()),
            ),
            patch("module.core.loops.Database", return_value=_async_cm(mock_db)),
            patch("module.core.loops.RSSEngine", return_value=mock_engine),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.notification.enable = False
            mock_settings.bangumi_manage.eps_complete = False
            await rss_tick(analyser, notifier)

        notifier.send_event.assert_awaited_once_with(events[0])


# ---------------------------------------------------------------------------
# rename_tick
# ---------------------------------------------------------------------------


class TestRenameTick:
    async def test_sends_notification_per_renamed_item(self):
        """Every item Renamer.rename() returns is forwarded to the notifier."""
        notify = Notification(official_title="Test Anime", season=1, episode=1)
        notifier = AsyncMock()

        mock_renamer = AsyncMock()
        mock_renamer.rename = AsyncMock(return_value=[notify])

        with (
            patch(
                "module.core.loops.DownloadClient",
                return_value=_async_cm(AsyncMock()),
            ),
            patch("module.core.loops.Renamer", return_value=mock_renamer),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.notification.enable = True
            await rename_tick(notifier)

        notifier.send_all.assert_awaited_once_with(notify)

    async def test_no_notification_sent_when_disabled(self):
        notify = Notification(official_title="Test Anime", season=1, episode=1)
        notifier = AsyncMock()

        mock_renamer = AsyncMock()
        mock_renamer.rename = AsyncMock(return_value=[notify])

        with (
            patch(
                "module.core.loops.DownloadClient",
                return_value=_async_cm(AsyncMock()),
            ),
            patch("module.core.loops.Renamer", return_value=mock_renamer),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.notification.enable = False
            await rename_tick(notifier)

        notifier.send_all.assert_not_awaited()

    async def test_dispatches_multiple_renamed_items_concurrently(self):
        """Regression: a batch rename (several episodes in one tick) must
        fan out notifications concurrently, not serialize one item's full
        round-trip after another (restores the cba4988 concurrent-dispatch
        optimization lost in the 3.3 core rewrite)."""
        notifications = [
            Notification(official_title=f"Anime {i}", season=1, episode=i)
            for i in range(5)
        ]
        notifier = AsyncMock()

        async def slow_send_all(_notify):
            await asyncio.sleep(0.05)

        notifier.send_all = AsyncMock(side_effect=slow_send_all)

        mock_renamer = AsyncMock()
        mock_renamer.rename = AsyncMock(return_value=notifications)

        with (
            patch(
                "module.core.loops.DownloadClient",
                return_value=_async_cm(AsyncMock()),
            ),
            patch("module.core.loops.Renamer", return_value=mock_renamer),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.notification.enable = True
            start = time.perf_counter()
            await rename_tick(notifier)
            elapsed = time.perf_counter() - start

        assert notifier.send_all.await_count == 5
        # Serial would take ~0.25s (5 x 0.05s); concurrent should stay well
        # under 2x a single call's latency.
        assert elapsed < 0.15


# ---------------------------------------------------------------------------
# update_check_tick
# ---------------------------------------------------------------------------


class TestUpdateCheckTick:
    def _result(self, **overrides):
        result = MagicMock()
        result.has_update = overrides.get("has_update", True)
        result.error = overrides.get("error", None)
        result.current = overrides.get("current", "3.3.0")
        result.latest = overrides.get("latest", "3.3.1")
        result.channel = overrides.get("channel", "beta")
        result.notes = overrides.get("notes", "release notes")
        return result

    async def test_emits_event_when_update_available(self):
        notifier = AsyncMock()

        with (
            patch(
                "module.core.loops.updater.check_update",
                new=AsyncMock(return_value=self._result()),
            ),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.update.channel = "beta"
            await update_check_tick(notifier)

        notifier.send_event.assert_awaited_once()
        event = notifier.send_event.await_args.args[0]
        assert isinstance(event, UpdateAvailableEvent)
        assert event.latest == "3.3.1"
        assert event.current == "3.3.0"
        assert event.channel == "beta"

    async def test_silent_when_no_update(self):
        notifier = AsyncMock()

        with (
            patch(
                "module.core.loops.updater.check_update",
                new=AsyncMock(return_value=self._result(has_update=False)),
            ),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.update.channel = "stable"
            await update_check_tick(notifier)

        notifier.send_event.assert_not_awaited()

    async def test_silent_on_check_error(self):
        """网络失败等 error 情况不产生通知（避免每天误报一条）。"""
        notifier = AsyncMock()

        with (
            patch(
                "module.core.loops.updater.check_update",
                new=AsyncMock(return_value=self._result(error="rate limited")),
            ),
            patch("module.core.loops.settings") as mock_settings,
        ):
            mock_settings.update.channel = "stable"
            await update_check_tick(notifier)

        notifier.send_event.assert_not_awaited()
