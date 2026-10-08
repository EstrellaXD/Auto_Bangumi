import asyncio
import hashlib
import hmac
import json

import httpx
import pytest
from webhook_on_event import WebhookOnEvent

from ab_sdk.events import OrganizedFile, TorrentOrganized
from ab_sdk.testing import create_plugin

ORGANIZED = TorrentOrganized(
    torrent_hash="abc",
    bangumi_id=1,
    files=(OrganizedFile(path="/a/b.mkv", kind="media"),),
)


def deliver(options: dict, status: int = 200):
    """返回 (收到的请求, 发送函数)。"""
    plugin, _ = create_plugin(WebhookOnEvent, options)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status)

    plugin.client_factory = lambda: httpx.AsyncClient(  # type: ignore[method-assign]
        transport=httpx.MockTransport(handler)
    )
    return seen, lambda: asyncio.run(plugin.on_event(ORGANIZED))


def test_on_event_selected_kind_posts_signed_json():
    seen, send = deliver({"url": "https://hook.test/x", "secret": "s3cret"})
    send()
    [request] = seen
    body = json.loads(request.content)
    assert body["kind"] == "torrent.organized"
    assert body["data"]["files"][0]["path"] == "/a/b.mkv"
    expected = hmac.new(b"s3cret", request.content, hashlib.sha256).hexdigest()
    assert request.headers["X-AB-Signature"] == expected


@pytest.mark.parametrize(
    "options",
    [
        {"url": ""},
        {"url": "https://hook.test/x", "events": ["rss_failure"]},
    ],
)
def test_on_event_unwanted_event_sends_nothing(options):
    seen, send = deliver(options)
    send()
    assert seen == []


def test_on_event_without_secret_omits_signature():
    seen, send = deliver({"url": "https://hook.test/x", "events": ["*"]})
    send()
    assert "X-AB-Signature" not in seen[0].headers


def test_on_event_server_error_is_logged_not_raised():
    seen, send = deliver({"url": "https://hook.test/x"}, status=500)
    send()
    assert len(seen) == 1
