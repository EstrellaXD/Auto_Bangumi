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


class ServerChanMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    desp: str = Field(..., description="description")


class ServerChanService(NotifierAdapter, NotifierRequestMixin):
    token: str = Field(..., description="server chan token")
    base_url: str = Field("https://sctapi.ftqq.com", description="server chan base url")

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        if notification:
            message = self.template.format(**notification.dict())
            data = ServerChanMessage(
                title=notification.official_title,
                desp=message,
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
            data = ServerChanMessage(desp=message)
            return data

        raise ValueError("Can't get notification or record input.")

    def send(self, **kwargs):
        data = self._process_input(**kwargs)
        loop = asyncio.get_event_loop()
        req = self.asend(
            entrypoint=f"/{self.token}.send",
            base_url=self.base_url,
            params=data.dict(),
        )
        res = loop.run_until_complete(req)

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
