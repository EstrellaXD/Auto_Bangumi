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
from module.utils.bangumi_data import get_poster
from module.utils.log import make_template

logger = logging.getLogger(__name__)


class WecomArticle(BaseModel):
    # see: https://developer.work.weixin.qq.com/document/path/90236#%E5%9B%BE%E6%96%87%E6%B6%88%E6%81%AF
    title: str = Field("AutoBangumi", description="title")
    description: str = Field(..., description="message")
    picurl: Optional[str] = Field(None, description="picurl")

    @validator("picurl")
    def set_placeholder_or_not(cls, v):
        # Default pic to avoid blank in message. Resolution:1068*455
        if v == "https://mikanani.me":
            return DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER
        return v


class WecomMessage(BaseModel):
    # see: https://developer.work.weixin.qq.com/document/path/90236#%E5%9B%BE%E6%96%87%E6%B6%88%E6%81%AF
    msgtype: str = Field("news", description="message type")
    agentid: str = Field(..., description="agent id")
    articles: list[WecomArticle] = Field(..., description="articles")


class WecomService(NotifierRequestMixin, NotifierAdapter):
    token: str = Field(..., description="wecom access token")
    agentid: str = Field(..., description="wecom agent id")
    base_url: str = Field(
        "https://qyapi.weixin.qq.com",
        description="wecom notification url",
    )

    @validator("base_url", pre=True)
    def set_default_base_url(cls, v):
        # make sure empty string will be set to default value
        if not v:
            return "https://qyapi.weixin.qq.com"
        return v

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.get("notification", None)
        record: Optional[logging.LogRecord] = kwargs.get("record", None)
        content: Optional[NotificationContent] = kwargs.get("content", None)

        data = WecomArticle(description="")

        if notification:
            data.description = self.template.format(**notification.dict())
            data.title = "【番剧更新】" + notification.official_title
            notification.poster_path = get_poster(notification.official_title)
            data.picurl = notification.poster_path

        elif record:
            data.description = make_template(record)
        elif content:
            data.description = content.content
        else:
            raise ValueError("Can't get notification or record input.")

        return WecomMessage(agentid=self.agentid, articles=[data])

    async def asend(self, **kwargs) -> Any:
        data = self._process_input(**kwargs)

        res = await super().asend(
            entrypoint="/cgi-bin/message/send",
            base_url=self.base_url,
            method="POST",
            params={"access_token": self.token},
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
