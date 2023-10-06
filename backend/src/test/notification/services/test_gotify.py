from unittest import mock
from aioresponses import aioresponses
from fastapi import params
import pytest
from module.notification.base import NotifierAdapter
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

    @pytest.mark.asyncio
    async def test__send(self, fake_notification):
        # Create a mock response for the HTTP request
        with aioresponses() as m:
            m.post(f"https://example.com/message?token={self.token}")

            data = GotifyMessage(
                title=fake_notification.official_title,
                message="test message",
                priority=10,
            )

            # Call the send method
            await self.gotify._send(data.dict())

            m.assert_called_once_with(
                "/message",
                method="POST",
                params={"token": self.token},
                data=data.dict(),
            )

    def test_send(self, fake_notification):
        with mock.patch("module.notification.services.gotify.GotifyService.send") as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = self.gotify.send(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    def test_send_failed(self, fake_notification):
        with mock.patch("module.notification.services.gotify.GotifyService.send") as m:
            m.return_value = None
            res = self.gotify.send(fake_notification)

            assert res is None
