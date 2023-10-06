import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp
from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import NotifierAdapter

logger = logging.getLogger(__name__)


class GotifyMessage(BaseModel):
    # see: https://gotify.net/api-docs#/message/createMessage
    priority: int = Field(5, description="priority", ge=0, le=10)
    message: str = Field(..., description="message")
    title: str = Field("AutoBangumi", description="title")
    extras: Optional[Dict[str, Any]] = Field(None, description="extras information")


class GotifyService(NotifierAdapter):
    """GotifyService is a class for gotify notification service"""

    token: str = Field(..., description="gotify client or app token")
    base_url: str = Field(..., description="gotify base url")

    async def _send(self, *args, **kwargs) -> Any:
        data = kwargs.get("data")
        try:
            async with aiohttp.ClientSession(base_url=self.base_url) as req:
                resp: aiohttp.ClientResponse = await req.post(
                    "/message", params={"token": self.token}, data=data
                )

                res = await resp.json()
                if not resp.ok:
                    logger.error(f"Can't send to bark because: {res}")
                    return

        except Exception as e:
            logger.error(f"Gotify notification error: {e}")

    def send(self, notification: Notification, *args, **kwargs):
        message = self.template.format(**notification.dict())

        # TODO: priority should be aliased with log level
        data = GotifyMessage(message=message).dict()
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data=data))

        if res:
            logger.debug(f"Gotify notification: {res}")

        return res
