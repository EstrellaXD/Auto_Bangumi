import asyncio
import logging
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from module.models import Notification
from module.notification.base import (
    DEFAULT_NOTIFICATION_IMAGE_PLACEHOLDER,
    NotifierAdapter,
    NotifierRequestMixin,
)
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
    articles: List[WecomArticle] = Field(..., description="articles")


class WecomService(NotifierAdapter, NotifierRequestMixin):
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
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        data = WecomArticle(description="")

        if notification:
            data.description = self.template.format(**notification.dict())
            data.title = "【番剧更新】" + notification.official_title
            data.picurl = notification.poster_path

        elif record:
            data.description = make_template(record)
        else:
            raise ValueError("Can't get notification or record input.")

        return WecomMessage(agentid=self.agentid, articles=[data])

    def send(self, **kwargs):
        data = self._process_input(**kwargs)
        loop = asyncio.get_event_loop()
        req = self.asend(
            entrypoint="/cgi-bin/message/send",
            base_url=self.base_url,
            method="POST",
            params={"access_token": self.token},
            data=data.dict(),
        )
        res = loop.run_until_complete(req)

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
