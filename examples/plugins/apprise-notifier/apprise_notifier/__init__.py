"""Apprise 通知渠道。

不依赖 apprise 库，而是调用用户自建的 Apprise API 服务器（caronc/apprise 镜像）：

- 填了 ``urls``：无状态调用 ``POST {server}/notify/``，请求体带上 Apprise URL；
- 否则用 ``config_key``：``POST {server}/notify/{config_key}``，URL 存在服务器上。

HTTP 2xx 即成功。接口文档：https://github.com/caronc/apprise-api
"""

from collections.abc import Callable
from typing import Any

import httpx2
from pydantic import BaseModel, Field

from ab_sdk import Plugin, points, provider
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Options(BaseModel):
    server: str = Field(
        "http://apprise:8000", title="服务器", description="Apprise API 服务器地址"
    )
    urls: list[str] = Field(
        default_factory=list,
        title="Apprise URL",
        description="如 tgram://bottoken/ChatID；填写后忽略配置键",
    )
    config_key: str = Field(
        "",
        title="配置键",
        description="未填 Apprise URL 时，使用服务器上保存的这份配置",
    )


class Channel:
    def __init__(
        self,
        options: Options,
        settings: NotifierSettings,
        client_factory: Callable[[], httpx2.AsyncClient],
    ) -> None:
        self.options = options
        self.settings = settings
        self.client_factory = client_factory

    async def _post(self, message: NotificationMessage) -> tuple[bool, str]:
        opts = self.options
        server = opts.server.rstrip("/")
        payload: dict[str, Any] = {"title": message.title, "body": message.body}
        if opts.urls:
            url = f"{server}/notify/"
            # Apprise 接受逗号分隔的 URL 字符串
            payload["urls"] = ", ".join(opts.urls)
        elif opts.config_key:
            url = f"{server}/notify/{opts.config_key}"
        else:
            return False, "需填写 Apprise URL 或配置键"
        try:
            async with self.client_factory() as client:
                resp = await client.post(url, json=payload)
        except httpx2.HTTPError as e:
            return False, f"请求失败：{e}"
        if resp.is_success:
            return True, "ok"
        return False, f"Apprise 返回 HTTP {resp.status_code}：{resp.text[:200]}"

    async def send(self, message: NotificationMessage) -> bool:
        ok, _ = await self._post(message)
        return ok

    async def test(self) -> tuple[bool, str]:
        return await self._post(
            NotificationMessage(
                kind="event", title="AutoBangumi 通知测试", body="通知测试成功！"
            )
        )


class AppriseNotifier(Plugin[Options]):
    config_model = Options

    # 测试可替换为带 MockTransport 的客户端
    client_factory: Callable[[], httpx2.AsyncClient] = staticmethod(
        lambda: httpx2.AsyncClient(timeout=10)
    )

    @provider(points.NOTIFIER, id="apprise")
    def channel(self) -> NotifierFactory:
        return lambda settings: Channel(self.config, settings, self.client_factory)
