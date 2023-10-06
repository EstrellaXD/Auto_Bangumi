from unittest import mock

import pytest
from aioresponses import aioresponses
from module.notification.base import NotifierAdapter
from module.notification.services.telegram import TelegramPhotoMessage, TelegramService


class TestTelegramPhotoMessage:
    def test_TelegramPhotoMessage(self):
        message = TelegramPhotoMessage(
            chat_id="123456789",
            caption="Test Caption",
            photo="https://example.com/image.jpg",
        )

        assert message.chat_id == "123456789"
        assert isinstance(message.chat_id, str)

        assert message.caption == "Test Caption"
        assert message.photo == "https://example.com/image.jpg"
        assert message.disable_notification is True


class TestTelegramService:
    def test_TelegramService_inherits_NotifierAdapter(self):
        assert issubclass(TelegramService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"
        cls.chat_id = "1111"
        cls.base_url = "https://example.com"

        cls.telegram = TelegramService(
            token=cls.token, chat_id=cls.chat_id, base_url=cls.base_url
        )

    def test_init_properties(self):
        assert self.telegram.token == self.token
        assert self.telegram.chat_id == self.chat_id
        assert self.telegram.base_url == self.base_url

    @pytest.mark.asyncio
    async def test__send(self, fake_notification):
        # Create a mock response for the HTTP request
        with aioresponses() as m:
            data = TelegramPhotoMessage(
                chat_id=self.chat_id,
                caption="Test Caption",
                photo=fake_notification.poster_path,
            )
            m.post(f"https://api.telegram.org/bot{self.token}/sendPhoto")

            # Call the send method
            await self.telegram._send(data.dict())

            m.assert_called_once_with(
                f"/bot{self.token}/sendPhoto",
                method="POST",
                data=data.dict(),
            )

    def test_send(self, fake_notification):
        with mock.patch(
            "module.notification.services.telegram.TelegramService.send"
        ) as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = self.telegram.send(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    def test_send_failed(self, fake_notification):
        with mock.patch(
            "module.notification.services.telegram.TelegramService.send"
        ) as m:
            m.return_value = None
            res = self.telegram.send(fake_notification)

            assert res is None
