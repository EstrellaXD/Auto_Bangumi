from unittest import mock

import pytest
from aioresponses import aioresponses
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


class TestBarkService:
    def test_BarkService_inherits_NotifierAdapter(self):
        assert issubclass(BarkService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"

        cls.bark = BarkService(token=cls.token)

    def test_init_properties(self):
        assert self.bark.token == self.token
        assert self.bark.base_url == "https://api.day.app"

    def test_send(self, fake_notification):
        with mock.patch("module.notification.services.bark.BarkService.send") as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = self.bark.send(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    def test_send_failed(self, fake_notification):
        with mock.patch("module.notification.services.bark.BarkService.send") as m:
            m.return_value = None
            res = self.bark.send(fake_notification)

            assert res is None