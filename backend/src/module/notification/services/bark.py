import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from pydantic import BaseModel, Field, validator

from module.models import Notification
from module.notification.base import (
    NotificationContent,
    NotifierAdapter,
    NotifierRequestMixin,
)
from module.utils.bangumi_data import get_poster
from module.utils.log import make_template

logger = logging.getLogger(__name__)


class BarkMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    body: str = Field(..., description="body")
    icon: Optional[str] = Field(None, description="icon")
    device_key: str = Field(..., description="device_key")


class BarkService(NotifierRequestMixin, NotifierAdapter):
    token: str = Field(..., description="device_key")
    base_url: str = Field("https://api.day.app", description="base_url")

    @validator("base_url", pre=True)
    def set_default_base_url(cls, v):
        # make sure empty string will be set to default value
        if not v:
            return "https://api.day.app"
        return v

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.get("notification", None)
        record: Optional[logging.LogRecord] = kwargs.get("record", None)
        content: Optional[NotificationContent] = kwargs.get("content", None)

        data = BarkMessage(body="", device_key=self.token)

        if notification:
            data.title = notification.official_title
            notification.poster_path = get_poster(notification.official_title)
            data.body = self.template.format(**notification.dict())
            data.icon = notification.poster_path
        elif record:
            data.body = make_template(record)
        elif content:
            data.body = content.content
        else:
            raise ValueError("Can't get notification or record input.")

        return data

    async def asend(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        # call NotifierRequestMixin.asend method
        res = await super().asend(
            entrypoint="/push",
            base_url=self.base_url,
            method="POST",
            data=data.dict(),
        )

        if res:
            logger.debug(f"Bark notification: {res}")

        return res

    def send(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(
                super().send,
                entrypoint="/push",
                base_url=self.base_url,
                method="POST",
                data=data.dict(),
            )

            res = future.result()

        if res:
            logger.debug(f"Bark notification: {res}")

        return res
