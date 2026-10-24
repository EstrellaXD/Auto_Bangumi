"""示例插件：Synology Chat 通知渠道。

向 Chat 的传入 Webhook 发送表单字段 ``payload=<JSON>``（Synology Chat 只接受这种
格式），JSON 为 ``{"text": ...}``，带海报时加 ``file_url``。Chat 即使拒绝也常返回
HTTP 200，结果在响应体的 ``success`` 里，所以两者都要检查。
"""

import json
from collections.abc import Callable

import httpx2
from pydantic import BaseModel

from ab_sdk import Plugin, points, provider, secret_field
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Options(BaseModel):
    webhook_url: str = secret_field(
        title="Webhook 地址",
        description="Chat → 整合 → 传入 Webhook 中的地址，含 token",
    )


def accepted(resp: httpx2.Response) -> bool:
    """2xx，且响应体是 JSON 时其中的 success 不为 false。"""
    if not resp.is_success:
        return False
    try:
        body = resp.json()
    except ValueError:
        return True
    return not isinstance(body, dict) or body.get("success", True) is not False


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
        payload: dict[str, str] = {"text": f"{message.title}\n{message.body}"}
        if message.poster_url:
            payload["file_url"] = message.poster_url
        data = {"payload": json.dumps(payload, ensure_ascii=False)}
        try:
            async with self.client_factory() as client:
                resp = await client.post(self.options.webhook_url, data=data)
        except httpx2.HTTPError:
            return False
        return accepted(resp)

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(
            NotificationMessage(kind="event", title="AutoBangumi", body="通知测试")
        )
        return ok, "ok" if ok else "发送失败"


class SynologyChatNotifier(Plugin[Options]):
    config_model = Options

    # 测试可替换为带 MockTransport 的客户端
    client_factory: Callable[[], httpx2.AsyncClient] = staticmethod(
        lambda: httpx2.AsyncClient(timeout=10)
    )

    @provider(points.NOTIFIER, id="synology-chat")
    def channel(self) -> NotifierFactory:
        return lambda settings: Channel(self.config, settings, self.client_factory)
