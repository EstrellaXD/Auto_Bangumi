import sqlite3

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
    async def test_get_total_notification(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_db = sqlite3.connect(":memory:")
        mocked_db.execute(
            "CREATE TABLE Queue (message_id TEXT, data TEXT, in_time INT, status INT)"
        )
        mocked_db.execute(
            "INSERT INTO Queue (message_id, data, in_time, status) VALUES (?, ?, ?, ?)",
            ("foo", "bar", 123, 0),
        )
        mocked_db.commit()

        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.conn = mocked_db

        resp = await aclient.get("/v1/notification/total")
        assert resp.status_code == 200
        assert resp.json() == dict(code=0, msg="success", data=dict(total=1))

    @pytest.mark.asyncio
    async def test_get_total_notification_with_exception(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_conn = mocker.MagicMock()
        mocked_cursor = mocker.MagicMock()
        mocked_conn.cursor.return_value = mocked_cursor
        mocked_cursor.execute.side_effect = Exception("unknown error")

        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.conn = mocked_conn

        resp = await aclient.get("/v1/notification/total")
        assert resp.status_code == 500
        assert resp.json() == dict(detail="unknown error")

    @pytest.mark.asyncio
    async def test_get_notification(
        self,
        aclient: AsyncClient,
        mocker: MockerFixture,
        fake_nanoseconds,
        fake_nanoseconds_datetime,
    ):
        mocked_db = sqlite3.connect(":memory:")
        mocked_db.row_factory = sqlite3.Row
        mocked_db.execute(
            "CREATE TABLE Queue (message_id TEXT, data TEXT, in_time INT, status INT)"
        )
        mocked_db.execute(
            "INSERT INTO Queue (message_id, data, in_time, status) VALUES (?, ?, ?, ?)",
            ("foo", "bar", fake_nanoseconds, 0),
        )
        mocked_db.commit()

        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.conn = mocked_db

        resp = await aclient.get("/v1/notification", params={"page": 1, "limit": 20})
        assert resp.status_code == 200
        assert resp.json() == dict(
            code=0,
            msg="success",
            data=dict(
                total=1,
                messages=[
                    dict(
                        id="foo",
                        content="bar",
                        datetime=fake_nanoseconds_datetime,
                        has_read=False,
                        title="AutoBangumi",
                    )
                ],
            ),
        )

    @pytest.mark.asyncio
    async def test_get_notification_with_not_found(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_db = sqlite3.connect(":memory:")
        mocked_db.execute(
            "CREATE TABLE Queue (message_id TEXT, data TEXT, in_time INT, status INT)"
        )

        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.conn = mocked_db

        resp = await aclient.get("/v1/notification")
        assert resp.json() == dict(
            code=0, msg="success", data=dict(total=0, messages=[])
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_notification_with_exception(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_conn = mocker.MagicMock()
        mocked_cursor = mocker.MagicMock()
        mocked_conn.cursor.return_value = mocked_cursor
        mocked_cursor.execute.side_effect = Exception("unknown error")

        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.conn = mocked_conn

        resp = await aclient.get("/v1/notification")
        assert resp.status_code == 500
        assert resp.json() == dict(detail="unknown error")

    @pytest.mark.asyncio
    async def test_set_notification_read(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.done = mocker.MagicMock()

        resp = await aclient.post(
            "/v1/notification/read", json={"message_ids": ["foo"]}
        )
        assert resp.status_code == 200
        assert resp.json() == dict(code=0, msg="success", data=dict())
        m.done.assert_called_once_with("foo")

    @pytest.mark.asyncio
    async def test_set_notification_read_with_exception(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_done = mocker.MagicMock(side_effect=Exception("unknown error"))
        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.done = mocked_done

        resp = await aclient.post(
            "/v1/notification/read", json={"message_ids": ["foo"]}
        )
        assert resp.status_code == 500
        assert resp.json() == dict(detail="unknown error")
        m.done.assert_called_once_with("foo")

    @pytest.mark.asyncio
    async def test_send_notification(self, aclient: AsyncClient, mocker: MockerFixture):
        m = mocker.patch.object(Notifier, "asend", return_value=None)

        resp = await aclient.post("/v1/notification/send", json=dict(content="fooo"))
        assert resp.status_code == 200
        assert resp.json() == dict(code=0, msg="success", data=dict())
        m.assert_awaited_once_with(content=self.content)

    @pytest.mark.asyncio
    async def test_send_notification_with_exception(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        m = mocker.patch.object(
            Notifier,
            "asend",
            side_effect=RuntimeError("system error"),
        )

        resp = await aclient.post("/v1/notification/send", json=dict(content="fooo"))
        assert resp.json() == dict(detail="system error")
        assert resp.status_code == 500
        m.assert_awaited_once_with(content=self.content)

    @pytest.mark.asyncio
    async def test_clean_notification(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_conn = sqlite3.connect(":memory:")
        mocked_conn.execute(
            "CREATE TABLE Queue (message_id TEXT, data TEXT, in_time INT, status INT)"
        )
        mocked_conn.execute(
            "INSERT INTO Queue (message_id, data, in_time, status) VALUES (?, ?, ?, ?)",
            ("foo", "bar", 123, 2),
        )
        mocked_conn.commit()

        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.conn = mocked_conn
        m.prune = mocker.MagicMock(return_value=None)

        resp = await aclient.get("/v1/notification/clean")
        assert resp.status_code == 200
        assert resp.json() == dict(code=0, msg="success", data=dict())

    @pytest.mark.asyncio
    async def test_clean_notification_with_exception(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.prune = mocker.MagicMock(side_effect=Exception("unknown error"))

        resp = await aclient.get("/v1/notification/clean")
        assert resp.status_code == 500
        assert resp.json() == dict(detail="unknown error")

    @pytest.mark.asyncio
    async def test_get_notification_by_id(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_get = mocker.MagicMock(
            return_value=dict(message_id="foo", data="bar", datetime=123)
        )
        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.get = mocked_get

        resp = await aclient.get("/v1/notification/get", params={"message_id": "foo"})
        assert resp.status_code == 200
        assert resp.json() == dict(
            code=0, msg="success", data=dict(message_id="foo", data="bar", datetime=123)
        )

        mocked_get.assert_called_once_with("foo")

    @pytest.mark.asyncio
    async def test_get_notification_by_not_found_id(
        self, aclient: AsyncClient, mocker: MockerFixture
    ):
        mocked_get = mocker.MagicMock(return_value=None)
        m = mocker.patch.object(Notifier, "q", return_value=object())
        m.get = mocked_get

        resp = await aclient.get("/v1/notification/get", params={"message_id": "foo"})
        assert resp.status_code == 404
        assert resp.json() == dict(detail="message not found")
