"""WPUSH 通知渠道。

POST JSON 到 WPUSH 接口；HTTP 2xx 且返回 JSON 的 ``code == 0`` 才算成功。
接口文档：https://wpush.cn/docs
"""

from collections.abc import Callable

import httpx2
from pydantic import BaseModel, Field

from ab_sdk import Plugin, points, provider, secret_field
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings

API_URL = "https://api.wpush.cn/api/v1/send"


class Options(BaseModel):
    apikey: str = secret_field(title="API Key", description="WPUSH 控制台中的 apikey")
    channel: str = Field(
        "wechat", title="推送渠道", description="如 wechat、sms、mail，见 WPUSH 文档"
    )
    topic_code: str = Field(
        "", title="群组编码", description="可选：推送到群组时填写 topic_code"
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
        if not opts.apikey:
            return False, "未填写 apikey"
        payload = {
            "apikey": opts.apikey,
            "title": message.title,
            "content": message.body,
            "channel": opts.channel.strip() or "wechat",
        }
        if opts.topic_code.strip():
            payload["topic_code"] = opts.topic_code.strip()
        try:
            async with self.client_factory() as client:
                resp = await client.post(API_URL, json=payload)
        except httpx2.HTTPError as e:
            return False, f"请求失败：{e}"
        try:
            body = resp.json()
        except ValueError:
            body = None
        if resp.is_success and isinstance(body, dict) and body.get("code") == 0:
            return True, "ok"
        detail = body.get("message") if isinstance(body, dict) else None
        if not resp.is_success:
            # 网关的错误页不是 JSON，先报 HTTP 状态
            detail = f"HTTP {resp.status_code}" + (f"，{detail}" if detail else "")
        return False, f"WPUSH 返回错误：{detail or '响应不是预期的 JSON'}"

    async def send(self, message: NotificationMessage) -> bool:
        ok, _ = await self._post(message)
        return ok

    async def test(self) -> tuple[bool, str]:
        return await self._post(
            NotificationMessage(
                kind="event", title="AutoBangumi 通知测试", body="通知测试成功！"
            )
        )


class WPushNotifier(Plugin[Options]):
    config_model = Options

    # 测试可替换为带 MockTransport 的客户端
    client_factory: Callable[[], httpx2.AsyncClient] = staticmethod(
        lambda: httpx2.AsyncClient(timeout=10)
    )

    @provider(points.NOTIFIER, id="wpush")
    def channel(self) -> NotifierFactory:
        return lambda settings: Channel(self.config, settings, self.client_factory)
