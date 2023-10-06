import asyncio
import logging
from typing import Any, Dict

import aiohttp
from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import NotifierAdapter

logger = logging.getLogger(__name__)


class ServerChanMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    desp: str = Field(..., description="description")


class ServerChanService(NotifierAdapter):
    token: str = Field(..., description="server chan token")
    base_url: str = Field("https://sctapi.ftqq.com", description="server chan base url")

    async def _send(self, data: Dict[str, Any]) -> Any:
        try:
            async with aiohttp.ClientSession(base_url=self.base_url) as session:
                resp: aiohttp.ClientResponse = await session.post(
                    f"/{self.token}.send", data=data
                )

                res = await resp.json()
                if not resp.ok:
                    logger.error(f"Can't send to server chan because: {res}")
                    return

        except Exception as e:
            logger.error(f"ServerChan notification error: {e}")

    def send(self, notification: Notification, *args, **kwargs):
        message = self.template.format(**notification.dict())

        data = ServerChanMessage(
            title=notification.official_title,
            desp=message,
        ).dict()

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data=data))

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
