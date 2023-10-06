import asyncio
import logging
from typing import Any, Dict

import aiohttp
from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import NotifierAdapter

logger = logging.getLogger(__name__)


class SlackMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    body: str = Field(..., description="body")
    device_key: str = Field(..., description="device_key")


class SlackService(NotifierAdapter):
    token: str = Field(..., description="slack token")
    base_url: str = Field(..., description="slack base url")

    async def _send(self, data: Dict[str, Any]) -> Any:
        try:
            async with aiohttp.ClientSession() as session:
                resp: aiohttp.ClientResponse = await session.post(
                    self.base_url, data=data
                )

                res = await resp.json()
                if not resp.ok:
                    logger.error(f"Can't send to telegram because: {res}")
                    return

        except Exception as e:
            logger.error(f"Slack notification error: {e}")

    def send(self, notification: Notification, *args, **kwargs):
        message = self.template.format(**notification.dict())

        data = SlackMessage(
            title=notification.official_title,
            body=message,
            device_key=self.token,
        ).dict()

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data=data))

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
