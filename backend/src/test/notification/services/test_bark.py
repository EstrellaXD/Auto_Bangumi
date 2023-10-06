from module.notification.base import NotifierAdapter
from module.notification.services.bark import BarkMessage, BarkService


class TestBarkMessage:
    def test_BarkMessage(self):
        message = BarkMessage(
            title="Test Title",
            body="Test Body",
            icon="https://example.com/image.jpg",
            device_key="YOUR_DEVICE_KEY",
        )

        assert message.title == "Test Title"
        assert message.body == "Test Body"
        assert message.icon == "https://example.com/image.jpg"
        assert message.device_key == "YOUR_DEVICE_KEY"

    def test_BarkMessage_default_properties(self):
        message = BarkMessage(
            body="Test Body",
            icon="https://example.com/image.jpg",
            device_key="YOUR_DEVICE_KEY",
        )

        assert message.title == "AutoBangumi"


class TestGotifyService:
    def test_GotifyService_inherits_NotifierAdapter(self):
        assert issubclass(BarkService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"
        cls.base_url = "https://example.com"

        cls.bark = BarkService(token=cls.token, base_url=cls.base_url)

    def test_init_properties(self):
        assert self.bark.token == self.token
        assert self.bark.base_url == self.base_url
