import asyncio
import logging
from typing import Any, Dict

import aiohttp
from attr import validate
from pydantic import BaseModel, Field, validator

from module.models import Notification
from module.notification.base import NotifierAdapter

logger = logging.getLogger(__name__)


class WecomMessage(BaseModel):
    key: str = Field(..., description="key")
    type: str = Field("news", description="message type")
    title: str = Field("AutoBangumi", description="title")
    msg: str = Field(..., description="message")
    picurl: str = Field(..., description="picurl")

    @validator("picurl")
    def set_placeholder_or_not(cls, v):
        # Default pic to avoid blank in message. Resolution:1068*455
        if v == "https://mikanani.me":
            return "https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png"
        return v


class WecomService(NotifierAdapter):
    token: str = Field(..., description="wecom token")
    chat_id: str = Field(..., description="wecom chat id")
    notification_url: str = Field(..., description="wecom notification url")

    async def _send(self, data: Dict[str, Any]) -> Any:
        try:
            async with aiohttp.ClientSession() as session:
                resp: aiohttp.ClientResponse = await session.post(
                    self.notification_url, data=data
                )

                res = await resp.json()
                if not resp.ok:
                    logger.error(f"Can't send to telegram because: {res}")
                    return

        except Exception as e:
            logger.error(f"Wecom notification error: {e}")

    def send(self, notification: Notification, *args, **kwargs):
        message = self.template.format(**notification.dict())

        title = "【番剧更新】" + notification.official_title

        data = WecomMessage(
            key=self.token,
            title=title,
            msg=message,
            picurl=notification.poster_path,
        ).dict()

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data=data))

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
