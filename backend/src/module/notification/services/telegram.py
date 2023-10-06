import asyncio
import logging
from typing import Any

import aiohttp
from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import NotifierAdapter

logger = logging.getLogger(__name__)


class TelegramPhotoMessage(BaseModel):
    # see: https://core.telegram.org/bots/api#sendphoto
    chat_id: int = Field(..., description="telegram channel name id")
    caption: str = Field(..., description="the caption for photo")
    photo: str = Field(..., description="the photo url")
    disable_notification: bool = True


class TelegramService(NotifierAdapter):
    """TelegramService is a class for telegram notification service"""

    token: str = Field(..., description="telegram bot token")
    chat_id: str = Field(..., description="telegram chat id")
    base_url: str = Field(
        "https://api.telegram.org/",
        description="telegram bot base url",
    )

    async def _send(self, *args, **kwargs) -> Any:
        data = kwargs.get("data")
        try:
            async with aiohttp.ClientSession(base_url=self.base_url) as req:
                resp: aiohttp.ClientResponse = await req.post(
                    f"/bot{self.token}/sendPhoto", data=data
                )

                res = await resp.json()
                if not resp.ok:
                    logger.error(f"Can't send to telegram because: {res}")
                    return

        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
            return e

    def send(self, notification: Notification, *args, **kwargs):
        message = self.template.format(**notification.dict())

        data = TelegramPhotoMessage(
            chat_id=self.chat_id,
            caption=message,
            photo=notification.poster_path,
        ).dict()

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data))

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
