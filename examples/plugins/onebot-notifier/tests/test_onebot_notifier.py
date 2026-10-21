import asyncio
import json

import httpx2
import pytest
from onebot_notifier import OneBotNotifier

from ab_sdk.notify import NotificationMessage, NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin

BASE = {"url": "http://bot:3000/", "target": 123}
POSTER = "https://ab.example.com/posters/a.jpg"


def channel(status: int, body: dict, options: dict | None = None, seen=None):
    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(request)
        return httpx2.Response(status, json=body)

    plugin, _ = create_plugin(OneBotNotifier, BASE if options is None else options)
    plugin.client_factory = lambda: httpx2.AsyncClient(  # type: ignore[method-assign]
        transport=httpx2.MockTransport(handler)
    )
    return plugin.channel()(NotifierSettings())


def episode(poster_url: str | None = None) -> NotificationMessage:
    return NotificationMessage(
        kind="episode", title="番剧", body="番剧 第1集", poster_url=poster_url
    )


class TestChannel(NotifierContract):
    def create(self):
        return channel(200, {"status": "ok", "retcode": 0})

    def create_failing(self):
        return channel(200, {"status": "failed", "retcode": 100, "wording": "不是好友"})


@pytest.mark.parametrize(
    ("message_type", "path", "id_key"),
    [
        ("private", "/send_private_msg", "user_id"),
        ("group", "/send_group_msg", "group_id"),
    ],
)
def test_send_posts_to_endpoint_with_target(message_type, path, id_key):
    seen: list[httpx2.Request] = []
    ch = channel(200, {"retcode": 0}, {**BASE, "message_type": message_type}, seen)
    assert asyncio.run(ch.send(episode())) is True
    [request] = seen
    assert request.url.path == path
    assert json.loads(request.content) == {
        id_key: 123,
        "message": [{"type": "text", "data": {"text": "番剧 第1集"}}],
    }


@pytest.mark.parametrize(
    ("send_poster", "poster_url", "with_image"),
    [(True, POSTER, True), (False, POSTER, False), (True, None, False)],
)
def test_send_adds_image_segment_only_with_poster(send_poster, poster_url, with_image):
    seen: list[httpx2.Request] = []
    ch = channel(200, {"status": "ok"}, {**BASE, "send_poster": send_poster}, seen)
    assert asyncio.run(ch.send(episode(poster_url))) is True
    segments = json.loads(seen[0].content)["message"]
    image = {"type": "image", "data": {"file": POSTER}}
    assert (segments[0] == image) is with_image
    assert segments[-1]["type"] == "text"


@pytest.mark.parametrize(("token", "header"), [("t0k", "Bearer t0k"), ("", None)])
def test_send_sets_bearer_header_only_with_token(token, header):
    seen: list[httpx2.Request] = []
    ch = channel(200, {"status": "ok"}, {**BASE, "access_token": token}, seen)
    assert asyncio.run(ch.send(episode())) is True
    assert seen[0].headers.get("Authorization") == header


def test_test_reports_failure_on_http_error():
    ok, detail = asyncio.run(channel(401, {"msg": "token 错误"}).test())
    assert ok is False
    assert "token 错误" in detail


def test_send_without_target_returns_false_without_request():
    seen: list[httpx2.Request] = []
    ch = channel(200, {"status": "ok"}, {"url": "http://bot:3000"}, seen)
    assert asyncio.run(ch.send(episode())) is False
    assert seen == []
