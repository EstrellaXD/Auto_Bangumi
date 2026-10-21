import asyncio
import json
from collections.abc import Callable

import httpx2
import pytest
from slack_notifier import SlackNotifier

from ab_sdk.notify import NotificationMessage, NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin

URL = "https://hooks.slack.com/services/T/B/x"


def channel(
    response: httpx2.Response | Callable[[dict], httpx2.Response],
    seen: list | None = None,
):
    plugin, _ = create_plugin(SlackNotifier, {"webhook_url": URL})

    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(request)
        if callable(response):
            return response(json.loads(request.content))
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


# Slack 取不到海报时拒绝带 blocks 的整条消息
def reject_blocks(body: dict) -> httpx2.Response:
    if "blocks" in body:
        return httpx2.Response(400, text="invalid_blocks")
    return httpx2.Response(200, text="ok")


def test_send_rejected_blocks_retries_once_with_text_only():
    seen: list[httpx2.Request] = []
    message = NotificationMessage(
        kind="episode", title="T", body="b", poster_url="https://p/1.jpg"
    )
    assert asyncio.run(channel(reject_blocks, seen).send(message)) is True
    first, retry = seen
    assert "blocks" in json.loads(first.content)
    assert json.loads(retry.content) == {"text": "*T*\nb"}


def test_send_text_only_failure_is_not_retried():
    seen: list[httpx2.Request] = []
    message = NotificationMessage(kind="event", title="t", body="b")
    ch = channel(httpx2.Response(400, text="invalid_payload"), seen)
    assert asyncio.run(ch.send(message)) is False
    assert len(seen) == 1


@pytest.mark.parametrize(
    ("status", "text"), [(403, "invalid_token"), (429, "rate_limited")]
)
def test_send_with_poster_other_failure_is_not_retried(status, text):
    # 只有 blocks 被拒才退回纯文字；其它失败重发可能重复投递
    seen: list[httpx2.Request] = []
    message = NotificationMessage(
        kind="episode", title="T", body="b", poster_url="https://p/1.jpg"
    )
    ch = channel(httpx2.Response(status, text=text), seen)
    assert asyncio.run(ch.send(message)) is False
    assert len(seen) == 1
