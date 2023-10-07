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

        if notification:
            message = self.template.format(**notification.dict())
            data = BarkMessage(
                title=notification.official_title,
                body=message,
                icon=notification.poster_path,
                device_key=self.token,
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
            data = BarkMessage(body=message, device_key=self.token)
            return data

        raise ValueError("Can't get notification or record input.")

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
