from unittest import mock

import pytest
from aioresponses import aioresponses
from module.notification.base import NotifierAdapter
from module.notification.services.slack import (
    SlackAttachment,
    SlackMessage,
    SlackService,
)


class TestSlackAttachment:
    def test_SlackAttachment(self):
        attachment = SlackAttachment(
            title="Test Title",
            text="Test Text",
            image_url="https://example.com/image.jpg",
        )

        assert attachment.title == "Test Title"
        assert attachment.text == "Test Text"
        assert attachment.image_url == "https://example.com/image.jpg"


class TestSlackMessage:
    def test_SlackMessage(self):
        attachment = SlackAttachment(
            title="Test Title",
            text="Test Text",
            image_url="https://example.com/image.jpg",
        )
        message = SlackMessage(
            channel="Test Channel",
            attechment=[attachment],
        )

        assert message.channel == "Test Channel"
        assert message.attechment == [attachment]


class TestSlackService:
    def test_SlackService_inherits_NotifierAdapter(self):
        assert issubclass(SlackService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"
        cls.channel = "YOUR_CHANNEL"
        cls.base_url = "https://example.com"

        cls.slack = SlackService(
            token=cls.token, channel=cls.channel, base_url=cls.base_url
        )

    def test_init_properties(self):
        assert self.slack.token == self.token
        assert self.slack.channel == self.channel
        assert self.slack.base_url == self.base_url

    def test_send(self, fake_notification):
        with mock.patch("module.notification.services.slack.SlackService.send") as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = self.slack.send(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    def test_send_failed(self, fake_notification):
        with mock.patch("module.notification.services.slack.SlackService.send") as m:
            m.return_value = None
            res = self.slack.send(fake_notification)

            assert res is None