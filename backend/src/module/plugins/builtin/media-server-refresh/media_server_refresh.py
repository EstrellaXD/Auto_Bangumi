"""内置插件：种子整理完成后通知媒体服务器刷新媒体库（订阅 ``torrent.organized``）。

收到第一个事件后等待 ``delay`` 秒，期间整理完成的所有种子合并成一次刷新请求。
同时订阅 hardlink 插件的 ``hardlink.linked``：文件放入媒体库后再刷新一次。
未填写服务器地址或 API Key 时什么也不做，所以默认启用也无副作用。

``torrent.organized`` 投递为「至少一次」：下载器中已整理的种子每次进程重启后
会再发布一次，已配置时重启后最多多出一次（合并后的）刷新。
"""

import asyncio
from collections.abc import Callable
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from ab_sdk import Plugin, PluginContext, secret_field, subscribe
from ab_sdk.events import Event, TorrentOrganized

ServerType = Literal["jellyfin", "emby", "plex"]


class Options(BaseModel):
    server: ServerType = Field("jellyfin", title="服务器类型")
    url: str = Field(
        "",
        title="服务器地址",
        description="如 http://192.168.1.10:8096（Plex 默认端口 32400）；留空则不刷新",
    )
    api_key: str = secret_field(
        title="API Key",
        description="Jellyfin / Emby 的 API Key，或 Plex 的 X-Plex-Token",
    )
    delay: float = Field(
        30,
        ge=0,
        le=3600,
        title="延迟（秒）",
        description="收到整理完成事件后等待多久再刷新，期间的事件合并为一次刷新",
    )


def build_request(options: Options) -> tuple[str, str, dict[str, str]]:
    """返回 (HTTP 方法, URL, 请求头)。"""
    base = options.url.strip().rstrip("/")
    key = options.api_key
    if options.server == "plex":
        return "GET", f"{base}/library/sections/all/refresh", {"X-Plex-Token": key}
    if options.server == "emby":
        return "POST", f"{base}/emby/Library/Refresh", {"X-Emby-Token": key}
    return (
        "POST",
        f"{base}/Library/Refresh",
        {"Authorization": f'MediaBrowser Token="{key}"'},
    )


class MediaServerRefresh(Plugin[Options]):
    config_model = Options

    def __init__(self, ctx: PluginContext) -> None:
        super().__init__(ctx)
        self._pending: asyncio.Task[None] | None = None
        # 刷新请求发出后又有新事件：这次刷新之后再排一次
        self._again = False
        # 测试可替换为带 MockTransport 的客户端
        self.client_factory: Callable[[], httpx.AsyncClient] = lambda: (
            httpx.AsyncClient(timeout=10)
        )

    @property
    def configured(self) -> bool:
        return bool(self.config.url.strip() and self.config.api_key)

    async def teardown(self) -> None:
        if self._pending is not None and not self._pending.done():
            self._pending.cancel()
            try:
                await self._pending
            except asyncio.CancelledError:
                pass
        self._pending = None

    @subscribe(TorrentOrganized.kind)
    async def on_organized(self, event: TorrentOrganized) -> None:
        self._schedule(event.kind)

    # hardlink 插件把文件放入媒体库后发布；跨盘复制可能比 delay 更久，
    # 放好后再刷新一次（期间的事件同样合并）
    @subscribe("hardlink.linked")
    async def on_linked(self, event: Event) -> None:
        self._schedule(event.kind)

    def _schedule(self, kind: str) -> None:
        if not self.configured:
            return
        if self._pending is None or self._pending.done():
            self.ctx.log.debug("收到 %s，计划刷新媒体库", kind)
            self._pending = asyncio.create_task(self._refresh_later())
        else:
            self._again = True

    async def _refresh_later(self) -> None:
        again = True
        while again:
            await asyncio.sleep(self.config.delay)
            # 等待期间到达的事件由这次刷新覆盖
            self._again = False
            try:
                await self.refresh()
            except Exception as e:
                self.ctx.log.warning("刷新媒体库失败：%s", e)
            again = self._again

    async def refresh(self) -> bool:
        method, url, headers = build_request(self.config)
        async with self.client_factory() as client:
            resp = await client.request(method, url, headers=headers)
        if resp.is_success:
            self.ctx.log.info("已请求 %s 刷新媒体库", self.config.server)
            return True
        self.ctx.log.warning(
            "%s 刷新媒体库失败：HTTP %s", self.config.server, resp.status_code
        )
        return False
