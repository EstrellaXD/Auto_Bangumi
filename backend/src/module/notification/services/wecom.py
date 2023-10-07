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

logger = logging.getLogger(__name__)


class WecomArticle(BaseModel):
    title: str = Field("AutoBangumi", description="title")
    description: str = Field(..., description="message")
    picurl: str = Field(..., description="picurl")

    @validator("picurl")
    def set_placeholder_or_not(cls, v):
        # Default pic to avoid blank in message. Resolution:1068*455
        if v == "https://mikanani.me":
            return "https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png"
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

    def _process_input(self, **kwargs):
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)

        if notification:
            message = self.template.format(**notification.dict())
            title = "【番剧更新】" + notification.official_title
            data = WecomMessage(
                agentid=self.agentid,
                articles=[
                    WecomArticle(
                        title=title,
                        description=message,
                        picurl=notification.poster_path,
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

            data = WecomMessage(
                agentid=self.agentid,
                articles=[
                    WecomArticle(
                        description=message,
                        picurl="https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png",
                    )
                ],
            )
            return data

        raise ValueError("Can't get notification or record input.")

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
