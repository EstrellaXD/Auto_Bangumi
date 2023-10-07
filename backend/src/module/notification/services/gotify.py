import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import (
    NotificationContent,
    NotifierAdapter,
    NotifierRequestMixin,
)
from module.utils.bangumi_data import get_poster
from module.utils.log import make_template

logger = logging.getLogger(__name__)


class GotifyMessage(BaseModel):
    # see: https://gotify.net/api-docs#/message/createMessage
    priority: int = Field(5, description="priority", ge=0, le=10)
    message: str = Field(..., description="message")
    title: str = Field("AutoBangumi", description="title")
    extras: Dict[str, Any] = Field(
        default_factory=dict, description="extras information"
    )


class GotifyService(NotifierRequestMixin, NotifierAdapter):
    """GotifyService is a class for gotify notification service"""

    token: str = Field(..., description="gotify client or app token")
    base_url: str = Field(..., description="gotify base url")

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.get("notification", None)
        record: Optional[logging.LogRecord] = kwargs.get("record", None)
        content: Optional[NotificationContent] = kwargs.get("content", None)

        data = GotifyMessage(message="")

        if notification:
            data.title = notification.official_title
            notification.poster_path = get_poster(notification.official_title)
            data.message = self.template.format(**notification.dict())
        elif record:
            data.message = make_template(record)
            data.priority = 8
        elif content:
            data.message = content.content
        else:
            raise ValueError("Can't get notification or record input.")

        return data

    async def asend(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        # call NotifierRequestMixin.asend method
        res = await super().asend(
            entrypoint="/message",
            base_url=self.base_url,
            method="POST",
            params={"token": self.token},
            data=data.dict(),
        )

        if res:
            logger.debug(f"Gotify notification: {res}")

        return res

    def send(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(
                super().send,
                entrypoint="/message",
                base_url=self.base_url,
                method="POST",
                params={"token": self.token},
                data=data.dict(),
            )

            res = future.result()

        if res:
            logger.debug(f"Gotify notification: {res}")

        return res
