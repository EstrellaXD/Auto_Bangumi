import logging
from unittest import mock

import pytest
from module.notification import Notifier, NotifierHandler


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

    def test__get_poster(self):
        with mock.patch("module.notification.Notifier._get_poster") as m:
            expected = "https://mikanani.me"
            m.return_value = expected

            res = self.notifier._get_poster(name="test")
            m.assert_called_once_with(name="test")
            assert res == expected

    def test__get_poster_failed(self):
        with mock.patch("module.notification.Notifier._get_poster") as m:
            m.return_value = ""

            res = self.notifier._get_poster(name="")
            m.assert_called_once_with(name="")
            assert res == ""

    def test_send(self, fake_notification):
        with mock.patch("module.notification.Notifier.send") as m:
            m.return_value = True
            assert self.notifier.send(notification=fake_notification)

            m.assert_called_once_with(notification=fake_notification)

    def test_send_with_side_effect(self, fake_notification):
        with mock.patch("module.notification.Notifier.send") as m:
            m.side_effect = Exception("Unexpected error.")
            with pytest.raises(Exception) as exc:
                self.notifier.send(notification=fake_notification)

            assert exc.match("Unexpected error.")
