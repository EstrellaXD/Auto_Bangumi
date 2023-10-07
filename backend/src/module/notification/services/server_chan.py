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


class ServerChanMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    desp: str = Field(..., description="description")


class ServerChanService(NotifierAdapter, NotifierRequestMixin):
    token: str = Field(..., description="server chan token")
    base_url: str = Field("https://sctapi.ftqq.com", description="server chan base url")

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        data = ServerChanMessage(desp="")

        if notification:
            data.title = notification.official_title
            data.desp = self.template.format(**notification.dict())
        elif record:
            data.desp = make_template(record)
        else:
            raise ValueError("Can't get notification or record input.")

        return data

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
