"""示例插件：Slack 通知渠道。

向 Incoming Webhook POST ``{"text": "*标题*\\n正文"}``（Slack 的 mrkdwn）。带海报时
再加 ``blocks``：一段文字加一张图片，``text`` 留作手机通知里的摘要。Slack 成功时
返回 HTTP 200 与响应体 ``ok``，失败时返回 4xx 与错误码（如 ``invalid_token``）。
"""

from collections.abc import Callable
from typing import Any

import httpx2
from pydantic import BaseModel

from ab_sdk import Plugin, points, provider, secret_field
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Options(BaseModel):
    webhook_url: str = secret_field(
        title="Webhook 地址",
        description="Slack App 的 Incoming Webhook 地址，形如 https://hooks.slack.com/services/...",
    )


def escape(text: str) -> str:
    """mrkdwn 只要求转义这三个字符（番剧名里常有 &）。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def slack_body(message: NotificationMessage) -> dict[str, Any]:
    text = f"*{escape(message.title)}*\n{escape(message.body)}"
    body: dict[str, Any] = {"text": text}
    if message.poster_url:
        body["blocks"] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {
                "type": "image",
                "image_url": message.poster_url,
                "alt_text": message.title,
            },
        ]
    return body


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

    async def send(self, message: NotificationMessage) -> bool:
        if not self.options.webhook_url:
            return False
        try:
            async with self.client_factory() as client:
                resp = await client.post(
                    self.options.webhook_url, json=slack_body(message)
                )
        except httpx2.HTTPError:
            return False
        return resp.is_success and resp.text == "ok"

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(
            NotificationMessage(kind="event", title="AutoBangumi", body="通知测试")
        )
        return ok, "ok" if ok else "发送失败"


class SlackNotifier(Plugin[Options]):
    config_model = Options

    # 测试可替换为带 MockTransport 的客户端
    client_factory: Callable[[], httpx2.AsyncClient] = staticmethod(
        lambda: httpx2.AsyncClient(timeout=10)
    )

    @provider(points.NOTIFIER, id="slack")
    def channel(self) -> NotifierFactory:
        return lambda settings: Channel(self.config, settings, self.client_factory)
