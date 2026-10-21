import asyncio
import json

import httpx2
import pytest
from slack_notifier import SlackNotifier

from ab_sdk.notify import NotificationMessage, NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin

URL = "https://hooks.slack.com/services/T/B/x"


def channel(response: httpx2.Response, seen: list | None = None):
    plugin, _ = create_plugin(SlackNotifier, {"webhook_url": URL})

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
        return channel(httpx2.Response(200, text="ok"))

    def create_failing(self):
        return channel(httpx2.Response(403, text="invalid_token"))


def sent_body(message: NotificationMessage) -> dict:
    seen: list[httpx2.Request] = []
    assert asyncio.run(channel(httpx2.Response(200, text="ok"), seen).send(message))
    return json.loads(seen[0].content)


def test_send_escapes_mrkdwn_and_bolds_title():
    body = sent_body(NotificationMessage(kind="event", title="A & <B>", body="x"))
    assert body == {"text": "*A &amp; &lt;B&gt;*\nx"}


def test_send_with_poster_adds_image_block():
    message = NotificationMessage(
        kind="episode", title="T", body="b", poster_url="https://p/1.jpg"
    )
    body = sent_body(message)
    assert body["text"] == "*T*\nb"
    assert body["blocks"][1] == {
        "type": "image",
        "image_url": "https://p/1.jpg",
        "alt_text": "T",
    }


@pytest.mark.parametrize("text", ["", "no_service"])
def test_send_2xx_without_ok_body_is_failure(text):
    message = NotificationMessage(kind="event", title="t", body="b")
    assert asyncio.run(channel(httpx2.Response(200, text=text)).send(message)) is False
