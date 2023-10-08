import pytest
from httpx import AsyncClient
from module.notification import Notifier
from module.notification.base import NotificationContent
from pytest_mock import MockerFixture


class TestNotificationAPI:
    @classmethod
    def setup_class(cls):
        cls.content = NotificationContent(content="fooo")

    @pytest.mark.asyncio
    async def test_send_notification(self, aclient: AsyncClient, mocker: MockerFixture):
        m = mocker.patch.object(Notifier, "asend", return_value=None)

        resp = await aclient.post("/v1/notification/send", json=dict(content="fooo"))
        assert resp.status_code == 200
        assert resp.json() == dict(code=0, msg="success")
        m.assert_awaited_once_with(content=self.content)

    @pytest.mark.asyncio
    async def test_send_notification_with_unexpected_exception(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        m = mocker.patch.object(
            Notifier,
            "asend",
            side_effect=RuntimeError("system error"),
        )

        resp = await aclient.post("/v1/notification/send", json=dict(content="fooo"))
        assert resp.status_code == 500
        assert resp.json() == dict(detail="system error")
        m.assert_awaited_once_with(content=self.content)
