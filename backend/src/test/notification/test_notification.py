import json
import logging
from unittest import mock

import pytest
from module.models.config import NotificationWebhookConfig
from module.notification import Notifier, NotifierHandler
from module.notification.base import NotificationWebhook
from pytest_httpx import HTTPXMock


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

    def test__get_json_with_notification(self, fake_notification):
        assert (
            self.notifier._get_json(notification=fake_notification)
            == fake_notification.json()
        )

    def test__get_json_with_record(self, fake_log_record):
        expected = dict(
            name=fake_log_record.name,
            level=fake_log_record.levelname,
            pathname=fake_log_record.pathname,
            lineno=fake_log_record.lineno,
            msg=fake_log_record.msg,
        )

        assert self.notifier._get_json(record=fake_log_record) == json.dumps(expected)

    def test__get_json_with_content(self, fake_content):
        assert self.notifier._get_json(content=fake_content) == fake_content.json()

    def test__get_json_with_invalid_args(self):
        kwargs = dict(hello="world!")
        with pytest.raises(ValueError) as exc:
            self.notifier._get_json(**kwargs)

        assert exc.match(f"Invalid input data: {kwargs}")

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
            self.notifier.send(notification=fake_notification)

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

    def test_send_webhook(
        self, httpx_mock: HTTPXMock, caplog: pytest.LogCaptureFixture
    ):
        caplog.set_level("DEBUG")
        httpx_mock.add_response(
            status_code=200,
            json={"message": "ok"},
        )

        webhook = NotificationWebhook(
            url="https://example.com",
            method="POST",
            body={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )
        self.notifier.send_webhook(webhook=webhook)

        httpx_mock.get_request(
            url="https://example.com/send",
            method="POST",
            match_headers={"Content-Type": "application/json"},
            match_json=b'{"hello": "world"}',
        )
        "Webhook response" in caplog.text

    def test_webhook_with_Exception(
        self, httpx_mock: HTTPXMock, caplog: pytest.LogCaptureFixture
    ):
        caplog.set_level("DEBUG")
        httpx_mock.add_exception(Exception("Request timeout"))

        webhook = NotificationWebhook(
            url="https://example.com",
            method="POST",
            body={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )
        self.notifier.send_webhook(webhook=webhook)

        httpx_mock.get_request(
            url="https://example.com/send",
            method="POST",
            match_headers={"Content-Type": "application/json"},
            match_json=b'{"hello": "world"}',
        )
        "Failed to send webhook" in caplog.text

    def test_send_webhook_with_NotificationWebhookConfig(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            status_code=200,
            json={"message": "ok"},
        )

        webhook_config = NotificationWebhookConfig(
            enable=True,
            url="https://example.com",
            method="POST",
            body={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )

        self.notifier.send_webhook(webhook=webhook_config)

        httpx_mock.get_request(
            url="https://example.com/send",
            method="POST",
            match_headers={"Content-Type": "application/json"},
            match_json=b'{"hello": "world"}',
        )
