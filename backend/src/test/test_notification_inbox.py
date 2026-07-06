"""通知中心持久化 sink：record_event / send_event 的 persist-first 语义。"""

from unittest.mock import AsyncMock, MagicMock, patch

from module.notification.events import RssFailureEvent, UpdateAvailableEvent
from module.notification.inbox import (
    bump_inbox_revision,
    inbox_revision,
    record_event,
)
from module.notification.manager import NotificationManager


def _async_cm(entered_value):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=entered_value)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _mock_db(upsert_return):
    db = MagicMock()
    db.inbox.upsert = AsyncMock(return_value=upsert_return)
    return db


EVENT = RssFailureEvent(rss_name="Feed", rss_url="http://x/rss", error="boom")


class TestRecordEvent:
    async def test_record_event_upserts_and_bumps_revision(self):
        row = MagicMock(id=7)
        db = _mock_db(row)
        before = inbox_revision()

        with patch("module.notification.inbox.Database", return_value=_async_cm(db)):
            result = await record_event(EVENT)

        assert result == 7
        assert inbox_revision() == before + 1
        kwargs = db.inbox.upsert.call_args.kwargs
        assert kwargs["kind"] == "rss_failure"
        assert kwargs["severity"] == "error"
        assert kwargs["dedup_key"] == "rss_failure:http://x/rss"
        assert kwargs["once"] is False
        assert "boom" in kwargs["payload"]
        assert kwargs["title"] == "RSS 订阅连接异常"

    async def test_record_event_once_skip_returns_zero_without_bump(self):
        db = _mock_db(None)  # upsert 返回 None = once 去重跳过
        before = inbox_revision()
        event = UpdateAvailableEvent(current="3.3.0", latest="3.3.1", channel="beta")

        with patch("module.notification.inbox.Database", return_value=_async_cm(db)):
            result = await record_event(event)

        assert result == 0
        assert inbox_revision() == before

    def test_bump_inbox_revision_increments(self):
        before = inbox_revision()
        bump_inbox_revision()
        assert inbox_revision() == before + 1


class TestSendEventPersistFirst:
    def _manager_with_provider(self):
        with patch("module.notification.manager.settings") as mock_settings:
            mock_settings.notification.providers = []
            manager = NotificationManager()
        provider = AsyncMock()
        provider.send_event = AsyncMock(return_value=True)
        provider.__aenter__ = AsyncMock(return_value=provider)
        provider.__aexit__ = AsyncMock(return_value=None)
        manager.providers = [provider]
        return manager, provider

    async def test_persists_but_does_not_broadcast_when_disabled(self):
        manager, provider = self._manager_with_provider()

        with (
            patch(
                "module.notification.manager.record_event", new_callable=AsyncMock
            ) as mock_record,
            patch("module.notification.manager.settings") as mock_settings,
        ):
            mock_settings.notification.enable = False
            await manager.send_event(EVENT)

        mock_record.assert_awaited_once_with(EVENT)
        provider.send_event.assert_not_awaited()

    async def test_persists_and_broadcasts_when_enabled(self):
        manager, provider = self._manager_with_provider()

        with (
            patch(
                "module.notification.manager.record_event", new_callable=AsyncMock
            ) as mock_record,
            patch("module.notification.manager.settings") as mock_settings,
        ):
            mock_settings.notification.enable = True
            await manager.send_event(EVENT)

        mock_record.assert_awaited_once_with(EVENT)
        provider.send_event.assert_awaited_once_with(EVENT)

    async def test_persist_failure_does_not_block_broadcast(self):
        manager, provider = self._manager_with_provider()

        with (
            patch(
                "module.notification.manager.record_event", new_callable=AsyncMock
            ) as mock_record,
            patch("module.notification.manager.settings") as mock_settings,
        ):
            mock_record.side_effect = RuntimeError("db locked")
            mock_settings.notification.enable = True
            await manager.send_event(EVENT)

        provider.send_event.assert_awaited_once_with(EVENT)
