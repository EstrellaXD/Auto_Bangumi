import asyncio
import json

import httpx2
from wpush_notifier import API_URL, WPushNotifier

from ab_sdk.notify import NotificationMessage, NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin


def channel(status: int, body: dict, options: dict | None = None, seen=None):
    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(request)
        return httpx2.Response(status, json=body)

    plugin, _ = create_plugin(
        WPushNotifier, {"apikey": "k"} if options is None else options
    )
    plugin.client_factory = lambda: httpx2.AsyncClient(  # type: ignore[method-assign]
        transport=httpx2.MockTransport(handler)
    )
    return plugin.channel()(NotifierSettings())


class TestChannel(NotifierContract):
    def create(self):
        return channel(200, {"code": 0, "message": "ok"})

    def create_failing(self):
        return channel(200, {"code": 1, "message": "apikey 无效"})


def test_send_posts_payload_with_topic_code():
    seen: list[httpx2.Request] = []
    ch = channel(
        200,
        {"code": 0},
        {"apikey": "k", "channel": "sms", "topic_code": "g1"},
        seen,
    )
    msg = NotificationMessage(kind="event", title="标题", body="正文")
    assert asyncio.run(ch.send(msg)) is True
    [request] = seen
    assert str(request.url) == API_URL
    assert json.loads(request.content) == {
        "apikey": "k",
        "title": "标题",
        "content": "正文",
        "channel": "sms",
        "topic_code": "g1",
    }


def test_test_reports_api_message_on_http_error():
    ok, detail = asyncio.run(channel(500, {"message": "内部错误"}).test())
    assert ok is False
    assert "内部错误" in detail


def test_send_without_apikey_returns_false_without_request():
    seen: list[httpx2.Request] = []
    ch = channel(200, {"code": 0}, {}, seen)
    assert asyncio.run(ch.test()) == (False, "未填写 apikey")
    assert seen == []
