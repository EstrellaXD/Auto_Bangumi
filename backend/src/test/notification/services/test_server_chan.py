from unittest import mock

import pytest
from aioresponses import aioresponses
from module.notification.base import NotifierAdapter
from module.notification.services.server_chan import (
    ServerChanMessage,
    ServerChanService,
)


class TestServerChanMessage:
    def test_ServerChanMessage(self):
        message = ServerChanMessage(
            title="Test title",
            desp="Test message",
        )

        assert message.title == "Test title"
        assert message.desp == "Test message"

    def test_ServerChanMessage_default_properties(self):
        message = ServerChanMessage(
            desp="Test message",
        )

        assert message.title == "AutoBangumi"


class TestServerChanService:
    def test_ServerChanService_inherits_NotifierAdapter(self):
        assert issubclass(ServerChanService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"
        cls.base_url = "https://example.com"

        cls.server_chan = ServerChanService(token=cls.token, base_url=cls.base_url)

    def test_init_properties(self):
        assert self.server_chan.token == self.token
        assert self.server_chan.base_url == self.base_url

    def test_send(self, fake_notification):
        with mock.patch(
            "module.notification.services.server_chan.ServerChanService.send"
        ) as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = self.server_chan.send(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    def test_send_failed(self, fake_notification):
        with mock.patch(
            "module.notification.services.server_chan.ServerChanService.send"
        ) as m:
            m.return_value = None
            res = self.server_chan.send(fake_notification)

            assert res is None
