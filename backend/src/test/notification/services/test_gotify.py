from unittest import mock

import pytest
from module.notification.base import NotificationContent, NotifierAdapter
from module.notification.services.gotify import GotifyMessage, GotifyService
from pydantic import ValidationError


class TestGotifyMessage:
    def test_GotifyMessage(self):
        message = GotifyMessage(
            priority=5,
            message="Test message",
            title="Test title",
            extras={"key": "value"},
        )

        assert message.priority == 5
        assert message.message == "Test message"
        assert message.title == "Test title"
        assert message.extras == {"key": "value"}

    def test_GotifyMessage_default_properties(self):
        message = GotifyMessage(
            message="Test message",
        )

        assert message.priority == 5
        assert message.title == "AutoBangumi"
        assert message.extras == {}

    def test_GotifyMessage_priority_bounce(self):
        with pytest.raises(ValidationError) as exc:
            GotifyMessage(
                priority=-1,
                message="Test message",
            )
        assert exc.match("ensure this value is greater than or equal to 0")

        with pytest.raises(ValidationError) as exc:
            GotifyMessage(
                priority=11,
                message="Test message",
            )

        assert exc.match("ensure this value is less than or equal to 10")


class TestGotifyService:
    def test_GotifyService_inherits_NotifierAdapter(self):
        assert issubclass(GotifyService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"
        cls.base_url = "https://example.com"

        cls.gotify = GotifyService(token=cls.token, base_url=cls.base_url)

    def test_init_properties(self):
        assert self.gotify.token == self.token
        assert self.gotify.base_url == self.base_url

    def test__process_input_with_notification(
        self, fake_notification, fake_notification_message
    ):
        with mock.patch.object(GotifyService, "_process_input") as m:
            m.return_value = GotifyMessage(
                priority=5,
                message=fake_notification_message,
                title=fake_notification.official_title,
                extras={},
            )

            message = self.gotify._process_input(notification=fake_notification)

            assert message.title == fake_notification.official_title
            assert message.message == fake_notification_message
            assert message.extras == {}

    def test__process_input_with_log_record(self, fake_log_record, fake_log_message):
        message = self.gotify._process_input(record=fake_log_record)

        assert message.title == "AutoBangumi"
        assert message.message == fake_log_message
        assert message.priority == 8
        assert message.extras == {}

    def test__process_input_with_content(self):
        message = self.gotify._process_input(
            content=NotificationContent(content="Test message")
        )

        assert message.title == "AutoBangumi"
        assert message.message == "Test message"
        assert message.priority == 5
        assert message.extras == {}

    def test_send(self, fake_notification):
        with mock.patch("module.notification.services.gotify.GotifyService.send") as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = self.gotify.send(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    def test_send_failed(self, fake_notification):
        with mock.patch("module.notification.services.gotify.GotifyService.send") as m:
            m.side_effect = Exception("Request Timeout")

            with pytest.raises(Exception) as exc:
                self.gotify.send(fake_notification)

            assert exc.match("Request Timeout")

    @pytest.mark.asyncio
    async def test_asend(self, fake_notification):
        with mock.patch("module.notification.services.gotify.GotifyService.asend") as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = await self.gotify.asend(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    @pytest.mark.asyncio
    async def test_asend_failed(self, fake_notification):
        with mock.patch("module.notification.services.gotify.GotifyService.asend") as m:
            m.side_effect = Exception("Request Timeout")

            with pytest.raises(Exception) as exc:
                await self.gotify.asend(fake_notification)

            assert exc.match("Request Timeout")
