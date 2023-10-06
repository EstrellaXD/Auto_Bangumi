import asyncio
import logging
from typing import Any, Dict, List

import aiohttp
from pydantic import BaseModel, Field, validator

from module.models import Notification
from module.notification.base import NotifierAdapter

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


class WecomService(NotifierAdapter):
    token: str = Field(..., description="wecom access token")
    agentid: str = Field(..., description="wecom agent id")
    base_url: str = Field(
        "https://qyapi.weixin.qq.com",
        description="wecom notification url",
    )

    async def _send(self, data: Dict[str, Any]) -> Any:
        async with aiohttp.ClientSession(base_url=self.base_url) as req:
            try:
                resp: aiohttp.ClientResponse = await req.post(
                    "/cgi-bin/message/send",
                    params={"access_token": self.token},
                    data=data,
                )

                res = await resp.json()
                if not resp.ok:
                    logger.error(f"Can't send to wecom because: {res}")
                    return

            except Exception as e:
                logger.error(f"Wecom notification error: {e}")

    def send(self, notification: Notification, *args, **kwargs):
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
        ).dict()

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self._send(data=data))

        if res:
            logger.debug(f"Telegram notification: {res}")

        return res
