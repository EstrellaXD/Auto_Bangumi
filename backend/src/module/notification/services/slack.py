import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from module.models import Notification
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    NotifierAdapter,
    NotifierRequestMixin,
)
from module.utils.log import make_template

logger = logging.getLogger(__name__)


class SlackAttachment(BaseModel):
    """SlackAttachment is a model for slack attachment.
    But this is a legacy model, it will be replace with block structure in the future.
    See:
        - https://api.slack.com/reference/messaging/attachments
        - https://api.slack.com/reference/block-kit/blocks
    """

    title: str = Field("AutoBangumi", description="title")
    text: str = Field(..., description="text")
    image_url: Optional[str] = Field(None, description="image url")


class SlackMessage(BaseModel):
    # see: https://api.slack.com/methods/chat.postMessage
    channel: str = Field(..., description="slack channel id")
    attechment: List[SlackAttachment] = Field(..., description="attechments")


class SlackService(NotifierAdapter, NotifierRequestMixin):
    token: str = Field(..., description="slack token")
    channel: str = Field(..., description="slack channel id")
    base_url: str = Field("https://slack.com", description="slack base url")

    @validator("base_url", pre=True)
    def set_default_base_url(cls, v):
        # make sure empty string will be set to default value
        if not v:
            return "https://slack.com"
        return v

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)
        data = SlackAttachment(text="")

        if notification:
            data.title = notification.official_title
            data.text = self.template.format(**notification.dict())
            data.image_url = notification.poster_path

        elif record:
            data.text = make_template(record)
        else:
            raise ValueError("Can't get notification or record input.")

        return SlackMessage(channel=self.channel, attechment=[data])

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
