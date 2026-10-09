"""示例插件：ntfy 通知渠道。

渠道凭据放在插件自己的配置里（``server``、``topic``、``token``），渠道条目只带
通用模板。后端拒绝消息时 ``send`` 返回 ``False``，不抛异常。
"""

from collections.abc import Callable

import httpx
from pydantic import BaseModel, Field

from ab_sdk import Plugin, points, provider, secret_field
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Options(BaseModel):
    server: str = Field("https://ntfy.sh", title="服务器")
    topic: str = Field("", title="主题")
    token: str = secret_field(title="访问令牌", description="私有主题的 Bearer 令牌")


class Channel:
    def __init__(
        self,
        options: Options,
        settings: NotifierSettings,
        client_factory: Callable[[], httpx.AsyncClient],
    ) -> None:
        self.options = options
        self.settings = settings
        self.client_factory = client_factory

    async def send(self, message: NotificationMessage) -> bool:
        opts = self.options
        if not opts.topic:
            return False
        # 标题含中文：httpx 的 str 头值只接受 ASCII，用 bytes 发 UTF-8
        headers = {b"Title": message.title.encode("utf-8")}
        if opts.token:
            headers[b"Authorization"] = f"Bearer {opts.token}".encode()
        try:
            async with self.client_factory() as client:
                resp = await client.post(
                    f"{opts.server.rstrip('/')}/{opts.topic}",
                    content=message.body.encode("utf-8"),
                    headers=headers,
                )
        except httpx.HTTPError:
            return False
        return resp.is_success

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(
            NotificationMessage(kind="event", title="AutoBangumi", body="通知测试")
        )
        return ok, "ok" if ok else "发送失败"


class NtfyNotifier(Plugin[Options]):
    config_model = Options

    # 测试可替换为带 MockTransport 的客户端
    client_factory: Callable[[], httpx.AsyncClient] = staticmethod(
        lambda: httpx.AsyncClient(timeout=10)
    )

    @provider(points.NOTIFIER, id="ntfy")
    def channel(self) -> NotifierFactory:
        return lambda settings: Channel(self.config, settings, self.client_factory)
