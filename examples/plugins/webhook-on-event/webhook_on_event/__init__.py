"""示例插件：事件 Webhook。

订阅全部事件（``@subscribe("*")``），只把配置里列出的 ``kind`` POST 到 ``url``。
请求体为 ``{"kind": ..., "data": {...}}``；配置了 ``secret`` 时，请求头
``X-AB-Signature`` 带请求体的 HMAC-SHA256（十六进制）。

接收方不可达只记日志：webhook 是外部服务，它的故障不应让插件被熔断。
"""

import hashlib
import hmac
import json
from collections.abc import Callable
from dataclasses import asdict

import httpx
from pydantic import BaseModel, Field

from ab_sdk import Event, Plugin, secret_field, subscribe


class Options(BaseModel):
    url: str = Field("", title="Webhook 地址", description="留空则什么也不发")
    events: list[str] = Field(
        default_factory=lambda: ["torrent.organized"],
        title="事件",
        description="要发送的事件 kind，如 torrent.organized、rss_failure；* 表示全部",
    )
    secret: str = secret_field(
        title="签名密钥", description="非空时在 X-AB-Signature 带请求体的 HMAC-SHA256"
    )


def encode(event: Event) -> bytes:
    """事件是冻结 dataclass；``default=str`` 兜住 Path 等非 JSON 类型。"""
    body = {"kind": event.kind, "data": asdict(event)}  # type: ignore[call-overload]
    return json.dumps(body, ensure_ascii=False, default=str).encode()


class WebhookOnEvent(Plugin[Options]):
    config_model = Options

    # 测试可替换为带 MockTransport 的客户端
    client_factory: Callable[[], httpx.AsyncClient] = staticmethod(
        lambda: httpx.AsyncClient(timeout=10)
    )

    def wants(self, event: Event) -> bool:
        cfg = self.config
        return bool(cfg.url) and ("*" in cfg.events or event.kind in cfg.events)

    @subscribe("*")
    async def on_event(self, event: Event) -> None:
        if not self.wants(event):
            return
        body = encode(event)
        headers = {"Content-Type": "application/json"}
        if self.config.secret:
            mac = hmac.new(self.config.secret.encode(), body, hashlib.sha256)
            headers["X-AB-Signature"] = mac.hexdigest()
        try:
            async with self.client_factory() as client:
                resp = await client.post(self.config.url, content=body, headers=headers)
        except httpx.HTTPError as e:
            self.ctx.log.warning("Webhook 请求失败：%s", e)
            return
        if not resp.is_success:
            self.ctx.log.warning("Webhook 返回 HTTP %s", resp.status_code)
