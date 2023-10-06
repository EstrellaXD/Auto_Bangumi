import asyncio
import logging
from typing import Any, Dict, List

import aiohttp
from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import NotifierAdapter

logger = logging.getLogger(__name__)


class SlackAttachment(BaseModel):
    title: str = Field(..., description="title")
    text: str = Field(..., description="text")
    image_url: str = Field(..., description="image url")


class SlackMessage(BaseModel):
    channel: str = Field(..., description="slack channel id")
    attechment: List[SlackAttachment] = Field(..., description="attechments")


class SlackService(NotifierAdapter):
    token: str = Field(..., description="slack token")
    channel: str = Field(..., description="slack channel id")
    base_url: str = Field("https://slack.com", description="slack base url")

    async def _send(self, data: Dict[str, Any]) -> Any:
        async with aiohttp.ClientSession(base_url=self.base_url) as req:
            try:
                resp: aiohttp.ClientResponse = await req.post(
                    "/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {self.token}"},
                    data=data,
                )

                return await resp.json()

            except Exception as e:
                logger.error(f"Slack notification error: {e}")

    def send(self, notification: Notification, *args, **kwargs):
        message = self.template.format(**notification.dict())

        data = SlackMessage(
            channel=self.channel,
            attechment=[
                SlackAttachment(
                    title=notification.official_title,
                    text=message,
                    image_url=notification.poster_path,
                )
            ],
        ).dict()

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data=data))

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
