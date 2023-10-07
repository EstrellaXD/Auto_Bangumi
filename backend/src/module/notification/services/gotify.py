import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from module.models import Notification
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    NotifierAdapter,
    NotifierRequestMixin,
)

logger = logging.getLogger(__name__)


class GotifyMessage(BaseModel):
    # see: https://gotify.net/api-docs#/message/createMessage
    priority: int = Field(5, description="priority", ge=0, le=10)
    message: str = Field(..., description="message")
    title: str = Field("AutoBangumi", description="title")
    extras: Dict[str, Any] = Field(
        default_factory=dict, description="extras information"
    )


class GotifyService(NotifierAdapter, NotifierRequestMixin):
    """GotifyService is a class for gotify notification service"""

    token: str = Field(..., description="gotify client or app token")
    base_url: str = Field(..., description="gotify base url")

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        if notification:
            message = self.template.format(**notification.dict())
            data = GotifyMessage(message=message)
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
            data = GotifyMessage(message=message, priority=8)
            return data

        raise ValueError("Can't get notification or record input.")

    def send(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)
        loop = asyncio.get_event_loop()
        req = self.asend(
            entrypoint="/message",
            base_url=self.base_url,
            method="POST",
            params={"token": self.token},
            data=data.dict(),
        )
        res = loop.run_until_complete(req)

        if res:
            logger.debug(f"Gotify notification: {res}")

        return res
