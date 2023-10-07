import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from pydantic import BaseModel, Field, validator

from module.models import Notification
from module.notification.base import (
    DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER,
    NotificationContent,
    NotifierAdapter,
    NotifierRequestMixin,
)
from module.utils.bangumi_data import get_poster
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

    @validator("base_url", pre=True)
    def set_default_base_url(cls, v):
        # make sure empty string will be set to default value
        if not v:
            return "https://api.telegram.org/"
        return v

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.get("notification", None)
        record: Optional[logging.LogRecord] = kwargs.get("record", None)
        content: Optional[NotificationContent] = kwargs.get("content", None)

        data = TelegramPhotoMessage(chat_id=self.chat_id, caption="")

        if notification:
            notification.poster_path = get_poster(notification.official_title)
            data.caption = self.template.format(**notification.dict())
            data.photo = notification.poster_path
        elif record:
            data.caption = make_template(record)
        elif content:
            data.caption = content.content
        else:
            raise ValueError("Can't get notification or record input.")

        return data

    async def asend(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        res = await super().asend(
            entrypoint=f"/bot{self.token}/sendPhoto",
            base_url=self.base_url,
            method="POST",
            data=data,
        )

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res

    def send(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(
                super().send,
                entrypoint=f"/bot{self.token}/sendPhoto",
                base_url=self.base_url,
                method="POST",
                data=data,
            )

            res = future.result()

        if res:
            logger.debug(f"Gotify notification: {res}")

        return res
