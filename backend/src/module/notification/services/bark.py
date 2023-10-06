import asyncio
import logging
from typing import Any, Dict

import aiohttp
from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import NotifierAdapter

logger = logging.getLogger(__name__)


class BarkMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    body: str = Field(..., description="body")
    icon: str = Field(..., description="icon")
    device_key: str = Field(..., description="device_key")


class BarkService(NotifierAdapter):
    token: str = Field(..., description="device_key")
    base_url: str = Field("https://api.day.app", description="base_url")

    async def _send(self, data: Dict[str, Any]) -> Any:
        try:
            async with aiohttp.ClientSession(base_url=self.base_url) as session:
                resp: aiohttp.ClientResponse = await session.post("/push", data=data)

                res = await resp.json()
                if not resp.ok:
                    logger.error(f"Can't send to bark because: {res}")
                    return

        except Exception as e:
            logger.error(f"Bark notification error: {e}")

    def send(self, notification: Notification, *args, **kwargs):
        message = self.template.format(**notification.dict())

        data = BarkMessage(
            title=notification.official_title,
            body=message,
            icon=notification.poster_path,
            device_key=self.token,
        ).dict()

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data=data))

        if res:
            logger.debug(f"Bark notification: {res}")

        return res
