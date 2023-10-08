import logging
from unittest import mock

import pytest
from module.notification import Notifier, NotifierHandler


class TestNotifierHandler:
    @classmethod
    def setup_class(cls):
        cls.handler = NotifierHandler(
            service_name="gotify",
            config=dict(
                token="YOUR_TOKEN",
                base_url="https://example.com",
            ),
        )
        logging.basicConfig(level=logging.DEBUG)
        cls.logger = logging.getLogger("test.TestNotifierHandler")
        cls.logger.addHandler(cls.handler)
        cls.logger.setLevel(logging.DEBUG)

    def test_emit(self, caplog):
        with mock.patch("module.notification.Notifier.send") as m:
            m.return_value = True
            self.logger.warning("test warning")
            caplog.set_level(logging.DEBUG, logger=self.logger.name)
            assert "test" in caplog.text


class TestNotifier:
    @classmethod
    def setup_class(cls):
        cls.notifier = Notifier(
            service_name="gotify",
            config=dict(
                token="YOUR_TOKEN",
                base_url="https://example.com",
            ),
        )

    def test_init_without_config(self):
        with pytest.raises(ValueError) as exc:
            Notifier(service_name="gotify")

        assert exc.match("Invalid notifier config")

    @pytest.mark.asyncio
    async def test_asend(self, fake_notification):
        with mock.patch("module.notification.Notifier.asend") as m:
            m.return_value = None
            await self.notifier.asend(notification=fake_notification)

            m.assert_called_once_with(notification=fake_notification)

    @pytest.mark.asyncio
    async def test_asend_with_side_effect(self, fake_notification):
        with mock.patch("module.notification.Notifier.asend") as m:
            m.side_effect = Exception("Unexpected error.")
            with pytest.raises(Exception) as exc:
                await self.notifier.asend(notification=fake_notification)

            assert exc.match("Unexpected error.")

    @pytest.mark.asyncio
    async def test_asend_with_log_capture(
        self,
        fake_notification,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        m = mock.MagicMock()
        monkeypatch.setitem(self.notifier.notifier.__dict__, "asend", m)
        m.side_effect = Exception("Request timeout")

        with caplog.at_level(logging.DEBUG, logger="module.notification"):
            await self.notifier.asend(notification=fake_notification)

        assert "Request timeout" in caplog.text

    def test_send(self, fake_notification):
        with mock.patch("module.notification.Notifier.send") as m:
            m.return_value = None
            assert self.notifier.send(notification=fake_notification)

            m.assert_called_once_with(notification=fake_notification)

    def test_send_with_side_effect(self, fake_notification):
        with mock.patch("module.notification.Notifier.send") as m:
            m.side_effect = Exception("Unexpected error.")
            with pytest.raises(Exception) as exc:
                self.notifier.send(notification=fake_notification)

            assert exc.match("Unexpected error.")

    def test_send_with_log_capture(
        self,
        fake_notification,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        m = mock.MagicMock()
        monkeypatch.setitem(self.notifier.notifier.__dict__, "send", m)
        m.side_effect = Exception("Request timeout")

        with caplog.at_level(logging.DEBUG, logger="module.notification"):
            self.notifier.send(notification=fake_notification)

        assert "Request timeout" in caplog.text
