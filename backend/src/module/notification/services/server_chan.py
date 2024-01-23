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


class ServerChanMessage(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    desp: str = Field(..., description="description")


class ServerChanService(NotifierRequestMixin, NotifierAdapter):
    token: str = Field(..., description="server chan token")
    base_url: str = Field("https://sctapi.ftqq.com", description="server chan base url")

    @validator("base_url", pre=True)
    def set_default_base_url(cls, v):
        # make sure empty string will be set to default value
        if not v:
            return "https://sctapi.ftqq.com"
        return v

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.get("notification", None)
        record: Optional[logging.LogRecord] = kwargs.get("record", None)
        content: Optional[NotificationContent] = kwargs.get("content", None)

        data = ServerChanMessage(desp="")

        if notification:
            data.title = notification.official_title
            notification.poster_path = get_poster(notification.official_title)
            data.desp = self.template.format(**notification.dict())
        elif record:
            data.desp = make_template(record)
        elif content:
            data.desp = content.content
        else:
            raise ValueError("Can't get notification or record input.")

        return data

    async def asend(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)
        res = await super().asend(
            entrypoint=f"/{self.token}.send",
            base_url=self.base_url,
            params=data.dict(),
        )

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res

    def send(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(
                super().send,
                entrypoint=f"/{self.token}.send",
                base_url=self.base_url,
                params=data.dict(),
            )
            res = future.result()

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
