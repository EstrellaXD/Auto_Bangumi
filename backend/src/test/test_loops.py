"""Tests for core/loops.py: notifier wiring for system events.

Covers the new call sites added for non-episode notifications (RSS failure,
download failure, offset review) -- the engine/scanner logic that produces
these events is already covered by test_rss_engine_new.py and
test_offset_scanner.py; these tests exercise the tick-level glue that turns
returned events into ``notifier.send_event`` calls, gated by
``settings.notification.enable``.
"""

from unittest.mock import AsyncMock, patch

from module.core.loops import offset_scan_tick, rss_tick
from module.notification.events import OffsetReviewEvent, RssFailureEvent

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

    async def test_no_events_sent_when_notifications_disabled(self):
        """settings.notification.enable=False suppresses all sends."""
        event = OffsetReviewEvent(official_title="Test Anime", reason="mismatch")
        notifier = AsyncMock()

        with patch("module.core.loops.OffsetScanner") as mock_scanner_cls:
            mock_scanner_cls.return_value.scan_all = AsyncMock(return_value=[event])
            with patch("module.core.loops.settings") as mock_settings:
                mock_settings.notification.enable = False
                await offset_scan_tick(notifier)

        notifier.send_event.assert_not_awaited()

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

    async def test_no_events_sent_when_notifications_disabled(self):
        """settings.notification.enable=False suppresses all sends."""
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

        notifier.send_event.assert_not_awaited()
