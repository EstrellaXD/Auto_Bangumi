"""OneBot v11 通知渠道。

POST JSON 到 ``{url}/send_private_msg`` 或 ``{url}/send_group_msg``，消息为消息段
数组：文字，以及（开启海报且宿主给出海报地址时）一张图片。HTTP 2xx 且返回
``status == "ok"`` 或 ``retcode == 0`` 才算成功。
协议文档：https://github.com/botuniverse/onebot-11
"""

from collections.abc import Callable
from typing import Any, Literal

import httpx2
from pydantic import BaseModel, Field

from ab_sdk import Plugin, points, provider, secret_field
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Options(BaseModel):
    url: str = Field(
        "",
        title="API 地址",
        description="OneBot v11 HTTP API 地址，如 http://napcat:3000",
    )
    access_token: str = secret_field(
        title="Access Token", description="可选：以 Authorization: Bearer 发送"
    )
    message_type: Literal["private", "group"] = Field("private", title="消息类型")
    target: int = Field(0, title="目标", description="私聊填 QQ 号，群聊填群号")
    send_poster: bool = Field(
        True,
        title="发送海报",
        description="需在通知设置里配置 base_url，宿主才会给出可访问的海报地址",
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

    def _segments(self, message: NotificationMessage) -> list[dict[str, Any]]:
        # 单集通知的正文已含番剧名；系统事件的标题与正文分开，拼在一起发
        text = (
            message.body
            if message.kind == "episode"
            else f"{message.title}\n{message.body}"
        )
        segments: list[dict[str, Any]] = []
        # SDK 只给出公开海报 URL（没有本地路径），由 OneBot 实现自行下载
        if self.options.send_poster and message.poster_url:
            segments.append({"type": "image", "data": {"file": message.poster_url}})
        segments.append({"type": "text", "data": {"text": text}})
        return segments

    async def _post(self, message: NotificationMessage) -> tuple[bool, str]:
        opts = self.options
        if not opts.url or not opts.target:
            return False, "未填写 API 地址或目标"
        id_key = "group_id" if opts.message_type == "group" else "user_id"
        headers = {}
        if opts.access_token:
            headers["Authorization"] = f"Bearer {opts.access_token}"
        try:
            async with self.client_factory() as client:
                resp = await client.post(
                    f"{opts.url.rstrip('/')}/send_{opts.message_type}_msg",
                    json={id_key: opts.target, "message": self._segments(message)},
                    headers=headers,
                )
            body = resp.json()
        except (httpx2.HTTPError, ValueError) as e:
            return False, f"请求失败：{e}"
        if (
            resp.is_success
            and isinstance(body, dict)
            and (body.get("status") == "ok" or body.get("retcode") == 0)
        ):
            return True, "ok"
        detail = (
            (body.get("wording") or body.get("msg")) if isinstance(body, dict) else None
        )
        return False, f"OneBot 返回错误：{detail or resp.status_code}"

    async def send(self, message: NotificationMessage) -> bool:
        ok, _ = await self._post(message)
        return ok

    async def test(self) -> tuple[bool, str]:
        return await self._post(
            NotificationMessage(
                kind="event", title="AutoBangumi 通知测试", body="通知测试成功！"
            )
        )


class OneBotNotifier(Plugin[Options]):
    config_model = Options

    # 测试可替换为带 MockTransport 的客户端
    client_factory: Callable[[], httpx2.AsyncClient] = staticmethod(
        lambda: httpx2.AsyncClient(timeout=10)
    )

    @provider(points.NOTIFIER, id="onebot")
    def channel(self) -> NotifierFactory:
        return lambda settings: Channel(self.config, settings, self.client_factory)
