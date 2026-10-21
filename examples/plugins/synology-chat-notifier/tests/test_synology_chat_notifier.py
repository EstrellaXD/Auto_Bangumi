import asyncio
import json
from urllib.parse import parse_qs

import httpx2
import pytest
from synology_chat_notifier import SynologyChatNotifier

from ab_sdk.notify import NotificationMessage, NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin

URL = "https://nas:5001/webapi/entry.cgi?api=SYNO.Chat.External&token=t"


def channel(response: httpx2.Response, seen: list | None = None):
    plugin, _ = create_plugin(SynologyChatNotifier, {"webhook_url": URL})

    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(request)
        return response

    plugin.client_factory = lambda: httpx2.AsyncClient(  # type: ignore[method-assign]
        transport=httpx2.MockTransport(handler)
    )
    return plugin.channel()(NotifierSettings())


class TestChannel(NotifierContract):
    def create(self):
        return channel(httpx2.Response(200, json={"success": True}))

    def create_failing(self):
        # Chat 拒绝请求时仍返回 HTTP 200
        return channel(httpx2.Response(200, json={"success": False, "error": {}}))


def test_send_posts_form_encoded_payload_json():
    seen: list[httpx2.Request] = []
    ch = channel(httpx2.Response(200, json={"success": True}), seen)
    message = NotificationMessage(
        kind="episode", title="新番更新", body="第 5 集", poster_url="https://p/1.jpg"
    )
    assert asyncio.run(ch.send(message)) is True
    [request] = seen
    assert str(request.url) == URL
    form = parse_qs(request.content.decode())
    assert json.loads(form["payload"][0]) == {
        "text": "新番更新\n第 5 集",
        "file_url": "https://p/1.jpg",
    }


@pytest.mark.parametrize(
    ("response", "ok"),
    [
        (httpx2.Response(200, text="ok"), True),
        (httpx2.Response(500, json={"success": True}), False),
    ],
)
def test_send_judges_status_and_optional_json_body(response, ok):
    message = NotificationMessage(kind="event", title="t", body="b")
    assert asyncio.run(channel(response).send(message)) is ok
