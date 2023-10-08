from unittest import mock

import pytest
from module.notification.base import (
    DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER,
    NotificationContent,
    NotifierAdapter,
)
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

        telegram = TelegramService(token=self.token, chat_id=self.chat_id, base_url="")
        assert telegram.base_url == "https://api.telegram.org/"

    def test__process_input_with_notification(
        self, fake_notification, fake_notification_message
    ):
        with mock.patch.object(TelegramService, "_process_input") as m:
            m.return_value = TelegramPhotoMessage(
                chat_id=self.telegram.chat_id,
                caption=fake_notification_message,
                photo=fake_notification.poster_path,
                disable_notification=True,
            )

            message = self.telegram._process_input(notification=fake_notification)

            assert message.chat_id == self.telegram.chat_id
            assert message.caption == fake_notification_message
            assert message.photo == fake_notification.poster_path
            assert message.disable_notification

    def test__process_input_with_log_record(self, fake_log_record, fake_log_message):
        message = self.telegram._process_input(record=fake_log_record)

        assert message.chat_id == self.telegram.chat_id
        assert message.caption == fake_log_message
        assert message.photo == DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER
        assert message.disable_notification

    def test__process_input_with_content(self):
        message = self.telegram._process_input(
            content=NotificationContent(content="Test message")
        )

        assert message.chat_id == self.telegram.chat_id
        assert message.caption == "Test message"
        assert message.photo == DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER
        assert message.disable_notification

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
            m.side_effect = Exception("Request Timeout")
            with pytest.raises(Exception) as exc:
                self.telegram.send(fake_notification)

            assert exc.match("Request Timeout")

    @pytest.mark.asyncio
    async def test_asend(self, fake_notification):
        with mock.patch(
            "module.notification.services.telegram.TelegramService.asend"
        ) as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value
            resp = await self.telegram.asend(fake_notification)

            m.assert_awaited_once_with(fake_notification)
            assert resp == return_value
