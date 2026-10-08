"""内置插件 media-server-refresh：订阅 torrent.organized，合并后请求媒体服务器刷新。"""

import asyncio
import logging
from types import SimpleNamespace

import httpx
import pytest

from ab_sdk.events import OrganizedFile, TorrentOrganized
from ab_sdk.hooks import SUBSCRIBE_ATTR
from ab_sdk.testing import create_plugin
from module.plugin.loader import BUILTIN_ROOT, discover


def load_candidate():
    candidates, errors = discover(
        local_root=BUILTIN_ROOT / "__missing__", entry_point_group="ab-test-none"
    )
    assert errors == []
    return {c.manifest.id: c for c in candidates}["media-server-refresh"]


def organized(n: int = 1) -> TorrentOrganized:
    return TorrentOrganized(
        torrent_hash=f"h{n}",
        bangumi_id=1,
        files=(OrganizedFile(f"/dl/A S01E0{n}.mkv", "media"),),
    )


def make_plugin(options, handler=None):
    plugin, _ = create_plugin(
        load_candidate().load(), options, plugin_id="media-server-refresh"
    )
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request) if handler else httpx.Response(204)

    plugin.client_factory = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(record)
    )
    return plugin, requests


def test_media_server_refresh_builtin_enabled_by_default_with_secret_key():
    candidate = load_candidate()
    assert candidate.source == "builtin"
    assert candidate.manifest.default_enabled is True
    schema = candidate.load().config_model.model_json_schema()
    assert schema["properties"]["api_key"]["secret"] is True


@pytest.mark.parametrize(
    "options", [{}, {"url": "http://jf:8096"}, {"api_key": "k"}, {"url": " "}]
)
async def test_on_organized_unconfigured_is_noop(options):
    plugin, requests = make_plugin(options)
    await plugin.on_organized(organized())
    assert plugin._pending is None
    await plugin.teardown()
    assert requests == []


@pytest.mark.parametrize(
    ("server", "method", "url", "header", "value"),
    [
        (
            "jellyfin",
            "POST",
            "http://srv:8096/Library/Refresh",
            "authorization",
            'MediaBrowser Token="k3y"',
        ),
        ("emby", "POST", "http://srv:8096/emby/Library/Refresh", "x-emby-token", "k3y"),
        (
            "plex",
            "GET",
            "http://srv:8096/library/sections/all/refresh",
            "x-plex-token",
            "k3y",
        ),
    ],
)
async def test_on_organized_burst_coalesces_into_one_refresh(
    server, method, url, header, value
):
    plugin, requests = make_plugin(
        {"server": server, "url": "http://srv:8096/", "api_key": "k3y", "delay": 0.05}
    )
    for n in range(1, 4):
        await plugin.on_organized(organized(n))
    assert plugin._pending is not None
    await asyncio.wait_for(plugin._pending, 1)

    assert len(requests) == 1
    assert requests[0].method == method
    assert str(requests[0].url) == url
    assert requests[0].headers[header] == value
    # 刷新完成后的新事件会再排一次
    await plugin.on_organized(organized(4))
    await asyncio.wait_for(plugin._pending, 1)
    assert len(requests) == 2


async def test_refresh_http_error_returns_false():
    plugin, requests = make_plugin(
        {"url": "http://srv", "api_key": "k"}, handler=lambda r: httpx.Response(401)
    )
    assert await plugin.refresh() is False
    assert len(requests) == 1


async def test_on_organized_connection_error_logged_without_secret(caplog):
    def explode(request):
        raise httpx.ConnectError("refused")

    plugin, _ = make_plugin(
        {"url": "http://srv", "api_key": "s3cr3t-key", "delay": 0}, handler=explode
    )
    with caplog.at_level(logging.WARNING):
        await plugin.on_organized(organized())
        assert plugin._pending is not None
        await asyncio.wait_for(plugin._pending, 1)
    assert "刷新媒体库失败" in caplog.text
    assert "s3cr3t-key" not in caplog.text


async def test_teardown_pending_refresh_cancelled():
    plugin, requests = make_plugin({"url": "http://srv", "api_key": "k", "delay": 60})
    await plugin.on_organized(organized())
    pending = plugin._pending
    assert pending is not None
    await plugin.teardown()
    assert pending.cancelled()
    assert requests == []


async def test_on_organized_during_refresh_request_refreshes_again():
    plugin, _ = make_plugin({"url": "http://srv", "api_key": "k", "delay": 0})
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            # 刷新请求已发出、尚未返回时又有种子整理完成
            await plugin.on_organized(organized(2))
        return httpx.Response(204)

    plugin.client_factory = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )
    await plugin.on_organized(organized(1))
    assert plugin._pending is not None
    await asyncio.wait_for(plugin._pending, 1)

    assert len(requests) == 2


async def test_hardlink_linked_event_schedules_refresh():
    plugin, requests = make_plugin({"url": "http://srv", "api_key": "k", "delay": 0})
    # 硬链接（跨盘复制可能比 delay 更久）放好文件后再刷新一次
    [handler] = [
        getattr(plugin, name)
        for name, member in vars(type(plugin)).items()
        if getattr(getattr(member, SUBSCRIBE_ATTR, None), "kind", None)
        == "hardlink.linked"
    ]

    await handler(SimpleNamespace(kind="hardlink.linked", torrent_hash="h1"))
    assert plugin._pending is not None
    await asyncio.wait_for(plugin._pending, 1)

    assert len(requests) == 1
