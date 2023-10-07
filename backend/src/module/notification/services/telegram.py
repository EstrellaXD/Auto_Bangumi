import asyncio
import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER,
    NotifierAdapter,
    NotifierRequestMixin,
)
from module.utils.log import make_template

logger = logging.getLogger(__name__)


class TelegramPhotoMessage(BaseModel):
    # see: https://core.telegram.org/bots/api#sendphoto
    chat_id: str = Field(..., description="telegram channel name id")
    caption: str = Field(..., description="the caption for photo")
    photo: str = Field(
        DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER, description="the photo url"
    )
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
        data = TelegramPhotoMessage(chat_id=self.chat_id, caption="")

        if notification:
            data.caption = self.template.format(**notification.dict())
            data.photo = notification.poster_path
        elif record:
            data.caption = make_template(record)
        else:
            raise ValueError("Can't get notification or record input.")

        return data

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
