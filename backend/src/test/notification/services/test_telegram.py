from module.notification.base import NotifierAdapter
from module.notification.services.telegram import TelegramPhotoMessage, TelegramService


class TestTelegramPhotoMessage:
    def test_TelegramPhotoMessage(self):
        message = TelegramPhotoMessage(
            chat_id=123456789,
            caption="Test Caption",
            photo="https://example.com/image.jpg",
        )

        assert message.chat_id == 123456789
        assert message.caption == "Test Caption"
        assert message.photo == "https://example.com/image.jpg"
        assert message.disable_notification is True


class TestTelegramService:
    def test_TelegramService_inherits_NotifierAdapter(self):
        assert issubclass(TelegramService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"
        cls.chat_id = "YOUR_CHAT_ID"
        cls.base_url = "https://example.com"

        cls.telegram = TelegramService(
            token=cls.token, chat_id=cls.chat_id, base_url=cls.base_url
        )

    def test_init_properties(self):
        assert self.telegram.token == self.token
        assert self.telegram.chat_id == self.chat_id
        assert self.telegram.base_url == self.base_url
