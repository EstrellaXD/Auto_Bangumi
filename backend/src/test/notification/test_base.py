from textwrap import dedent

import httpx
import pytest
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    DEFAULT_MESSAGE_TEMPLATE,
    NotificationContent,
    NotificationWebhook,
    NotifierAdapter,
    NotifierRequestMixin,
)
from pydantic import ValidationError
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from tenacity import RetryError


def test_default_message_template(fake_notification):
    content = DEFAULT_MESSAGE_TEMPLATE.format(**fake_notification.dict())
    expected = dedent(
        """\
        番剧名称：AutoBangumi Test
        季度：第1季
        更新集数：第1集
        https://test.com
        """
    )

    assert content == expected


def test_default_log_template():
    content = DEFAULT_LOG_TEMPLATE.format(
        dt="2021-08-15 21:58:44,123",
        levelname="INFO",
        msg="test message",
    )
    expected = dedent(
        """\
        日志时间：2021-08-15 21:58:44,123
        日志等级：INFO
        日志消息：test message
        """
    )

    assert content == expected


class TestNotifierAdapter:
    def test_not_implementation_send(self, fake_notification):
        with pytest.raises(NotImplementedError) as exc:
            NotifierAdapter.send(fake_notification)

        assert exc.match("send method is not implemented yet.")

    @pytest.mark.asyncio
    async def test_not_implementation_asend(self, fake_notification):
        with pytest.raises(NotImplementedError) as exc:
            await NotifierAdapter.asend(fake_notification)

        assert exc.match("send method is not implemented yet.")


class TestNotifierRequestMixin:
    @pytest.mark.asyncio
    async def test_asend(self, httpx_mock: HTTPXMock):
        def custom_response(request: httpx.Request):
            return httpx.Response(status_code=200, json={"hello": "world"})

        httpx_mock.add_callback(custom_response)

        resp = await NotifierRequestMixin().asend(
            entrypoint="/send",
            base_url="https://example.com",
            method="POST",
            params={"foo": "bar"},
            data={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )

        assert resp == {"hello": "world"}

        httpx_mock.get_request(
            url="https://example.com",
            method="POST",
            match_json={"hello": "world"},
            match_headers={"Content-Type": "application/json"},
        )

    @pytest.mark.asyncio
    async def test_asend_with_retry_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(Exception("Request Timeout"))

        with pytest.raises(Exception) as exc:
            await NotifierRequestMixin().asend(
                entrypoint="/send",
                base_url="https://example.com",
                method="POST",
                params={"foo": "bar"},
                data={"hello": "world"},
                headers={"Content-Type": "application/json"},
            )

            httpx_mock.get_request(
                url="https://example.com/send",
                params={"foo": "bar"},
                data={"hello": "world"},
                headers={"Content-Type": "application/json"},
            )

        assert exc.match("RetryError")

    def test_send(self, mocker: MockerFixture):
        m = mocker.patch.object(NotifierRequestMixin, "send", return_value="ok")

        NotifierRequestMixin().send(
            entrypoint="/send",
            base_url="https://example.com",
            method="POST",
            params={"foo": "bar"},
            data={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )

        m.assert_called_once_with(
            entrypoint="/send",
            base_url="https://example.com",
            method="POST",
            params={"foo": "bar"},
            data={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )

    def test_send_with_retry_error(self, mocker: MockerFixture):
        m = mocker.patch.object(
            NotifierRequestMixin,
            "send",
            side_effect=RetryError("RetryError"),
        )

        with pytest.raises(RetryError) as exc:
            NotifierRequestMixin().send(
                entrypoint="/send",
                base_url="https://example.com",
                method="POST",
                params={"foo": "bar"},
                data={"hello": "world"},
                headers={"Content-Type": "application/json"},
            )

        assert exc.match("RetryError")

        m.assert_called_once_with(
            entrypoint="/send",
            base_url="https://example.com",
            method="POST",
            params={"foo": "bar"},
            data={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )


def test_NotificationContent():
    content = NotificationContent(content="Test message")
    assert content.content == "Test message"
    assert content.dict() == {"content": "Test message"}


class TestNotificationWebhook:
    def test_init_property(self):
        webhook = NotificationWebhook(
            url="https://example.com",
            method="POST",
            params={"foo": "bar"},
            data={"hello": "world"},
            headers={"Content-Type": "application/json"},
        )

        assert webhook.url == "https://example.com"
        assert webhook.method == "POST"
        assert webhook.query == {"foo": "bar"}
        assert webhook.body == {"hello": "world"}
        assert webhook.headers == {"Content-Type": "application/json"}
        assert webhook.dict() == {
            "url": "https://example.com",
            "method": "POST",
            "query": {"foo": "bar"},
            "body": {"hello": "world"},
            "headers": {"Content-Type": "application/json"},
        }

        assert webhook.dict(by_alias=True) == {
            "url": "https://example.com",
            "method": "POST",
            "params": {"foo": "bar"},
            "data": {"hello": "world"},
            "headers": {"Content-Type": "application/json"},
        }

    def test_method_upper_case_validation(self):
        webhook = NotificationWebhook(url="http://example.com", method="post")
        assert webhook.method == "POST"

    def test_method_with_unsupported_value(self):
        with pytest.raises(ValidationError) as exc:
            NotificationWebhook(url="http://example.com", method="put")

        assert exc.match("method must be GET or POST")

    def test_optional_properties(self):
        webhook = NotificationWebhook(url="http://example.com", method="GET")
        assert webhook.query == {}
        assert webhook.body == {}
        assert webhook.headers == {}
