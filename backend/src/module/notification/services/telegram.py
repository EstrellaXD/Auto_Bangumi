import asyncio
import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    NotifierAdapter,
    NotifierRequestMixin,
)

logger = logging.getLogger(__name__)


class TelegramPhotoMessage(BaseModel):
    # see: https://core.telegram.org/bots/api#sendphoto
    chat_id: str = Field(..., description="telegram channel name id")
    caption: str = Field(..., description="the caption for photo")
    photo: str = Field(..., description="the photo url")
    disable_notification: bool = True


class TelegramService(NotifierAdapter, NotifierRequestMixin):
    """TelegramService is a class for telegram notification service"""

    token: str = Field(..., description="telegram bot token")
    chat_id: str = Field(..., description="telegram chat id")
    base_url: str = Field(
        "https://api.telegram.org/",
        description="telegram bot base url",
    )

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        if notification:
            message = self.template.format(**notification.dict())
            data = TelegramPhotoMessage(
                chat_id=self.chat_id,
                caption=message,
                photo=notification.poster_path,
            )
            return data

        if record:
            if hasattr(record, "asctime"):
                dt = record.asctime
            else:
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            message = DEFAULT_LOG_TEMPLATE.format(
                dt=dt,
                levelname=record.levelname,
                msg=record.msg,
            )

            data = TelegramPhotoMessage(
                chat_id=self.chat_id,
                caption=message,
                photo="https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png",
            )

        raise ValueError("Can't get notification or record input.")

    def send(self, **kwargs):
        data = self._process_input(**kwargs)
        loop = asyncio.get_event_loop()
        req = self.asend(
            entrypoint=f"/bot{self.token}/sendPhoto",
            base_url=self.base_url,
            method="POST",
            data=data,
        )
        res = loop.run_until_complete(req)

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
