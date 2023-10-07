import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    NotifierAdapter,
    NotifierRequestMixin,
)

logger = logging.getLogger(__name__)


class SlackAttachment(BaseModel):
    title: str = Field(..., description="title")
    text: str = Field(..., description="text")
    image_url: str = Field(..., description="image url")


class SlackMessage(BaseModel):
    channel: str = Field(..., description="slack channel id")
    attechment: List[SlackAttachment] = Field(..., description="attechments")


class SlackService(NotifierAdapter, NotifierRequestMixin):
    token: str = Field(..., description="slack token")
    channel: str = Field(..., description="slack channel id")
    base_url: str = Field("https://slack.com", description="slack base url")

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        if notification:
            message = self.template.format(**notification.dict())
            data = SlackMessage(
                channel=self.channel,
                attechment=[
                    SlackAttachment(
                        title=notification.official_title,
                        text=message,
                        image_url=notification.poster_path,
                    )
                ],
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

            data = SlackMessage(
                channel=self.channel,
                attechment=[
                    SlackAttachment(
                        title="AutoBangumi",
                        text=message,
                    )
                ],
            )
            return data

        raise ValueError("Can't get notification or record input.")

    def send(self, **kwargs):
        data = self._process_input(**kwargs)
        loop = asyncio.get_event_loop()
        req = self.asend(
            entrypoint="/api/chat.postMessage",
            base_url=self.base_url,
            method="POST",
            headers={"Authorization": f"Bearer {self.token}"},
            data=data.dict(),
        )
        res = loop.run_until_complete(req)

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
