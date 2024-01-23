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
    attechment: list[SlackAttachment] = Field(..., description="attechments")


class SlackService(NotifierRequestMixin, NotifierAdapter):
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
        notification: Optional[Notification] = kwargs.get("notification", None)
        record: Optional[logging.LogRecord] = kwargs.get("record", None)
        content: Optional[NotificationContent] = kwargs.get("content", None)

        data = SlackAttachment(text="")

        if notification:
            data.title = notification.official_title
            # TODO: get raw poster link
            # notification.poster_path = get_poster(notification.official_title)
            notification.poster_path = DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER
            data.text = self.template.format(**notification.dict())
            data.image_url = notification.poster_path

        elif record:
            data.text = make_template(record)
        elif content:
            data.text = content.content
        else:
            raise ValueError("Can't get notification or record input.")

        return SlackMessage(channel=self.channel, attechment=[data])

    async def asend(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)
        res = await super().asend(
            entrypoint="/api/chat.postMessage",
            base_url=self.base_url,
            method="POST",
            headers={"Authorization": f"Bearer {self.token}"},
            data=data.dict(),
        )

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res

    def send(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(
                super().send,
                entrypoint="/api/chat.postMessage",
                base_url=self.base_url,
                method="POST",
                headers={"Authorization": f"Bearer {self.token}"},
                data=data.dict(),
            )

            res = future.result()

        if res:
            logger.debug(f"Gotify notification: {res}")

        return res
