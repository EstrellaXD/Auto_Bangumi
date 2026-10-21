import asyncio
import json

import httpx2
import pytest
from apprise_notifier import AppriseNotifier

from ab_sdk.notify import NotificationMessage, NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin

MESSAGE = NotificationMessage(kind="event", title="标题", body="正文")


def channel(status: int, options: dict, seen=None):
    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(request)
        return httpx2.Response(status)

    plugin, _ = create_plugin(AppriseNotifier, options)
    plugin.client_factory = lambda: httpx2.AsyncClient(  # type: ignore[method-assign]
        transport=httpx2.MockTransport(handler)
    )
    return plugin.channel()(NotifierSettings())


class TestChannel(NotifierContract):
    def create(self):
        return channel(200, {"config_key": "ab"})

    def create_failing(self):
        return channel(424, {"config_key": "ab"})


@pytest.mark.parametrize(
    ("options", "path", "payload"),
    [
        (
            {"server": "http://ap:8000/", "urls": ["tgram://t/1", "mailto://u"]},
            "/notify/",
            {"title": "标题", "body": "正文", "urls": "tgram://t/1, mailto://u"},
        ),
        (
            {"server": "http://ap:8000", "config_key": "ab"},
            "/notify/ab",
            {"title": "标题", "body": "正文"},
        ),
    ],
)
def test_send_posts_stateless_urls_or_config_key(options, path, payload):
    seen: list[httpx2.Request] = []
    assert asyncio.run(channel(200, options, seen).send(MESSAGE)) is True
    [request] = seen
    assert request.url.path == path
    assert json.loads(request.content) == payload


def test_missing_urls_and_config_key_fails_without_request():
    seen: list[httpx2.Request] = []
    ch = channel(200, {}, seen)
    assert asyncio.run(ch.send(MESSAGE)) is False
    assert asyncio.run(ch.test()) == (False, "需填写 Apprise URL 或配置键")
    assert seen == []
