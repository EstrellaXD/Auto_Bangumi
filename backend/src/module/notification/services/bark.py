import asyncio
import logging
from typing import Optional

from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import (
    NotifierAdapter,
    NotifierRequestMixin,
)
from module.utils.log import make_template

logger = logging.getLogger(__name__)


class BarkMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    body: str = Field(..., description="body")
    icon: Optional[str] = Field(None, description="icon")
    device_key: str = Field(..., description="device_key")


class BarkService(NotifierAdapter, NotifierRequestMixin):
    token: str = Field(..., description="device_key")
    base_url: str = Field("https://api.day.app", description="base_url")

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        data = BarkMessage(body="", device_key=self.token)

        if notification:
            data.title = notification.official_title
            data.body = self.template.format(**notification.dict())
            data.icon = notification.poster_path
        elif record:
            data.body = make_template(record)
        else:
            raise ValueError("Can't get notification or record input.")

        return data

    def send(self, **kwargs):
        data = self._process_input(**kwargs)
        loop = asyncio.get_event_loop()
        req = self.asend(
            entrypoint="/push",
            base_url=self.base_url,
            method="POST",
            data=data.dict(),
        )
        res = loop.run_until_complete(req)

        if res:
            logger.debug(f"Bark notification: {res}")

        return res
