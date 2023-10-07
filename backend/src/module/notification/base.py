import logging
from abc import ABC, abstractmethod
from textwrap import dedent
from typing import Any, Dict, Literal, Optional

import aiohttp
from pydantic import BaseModel, Field
from tenacity import after_log, retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

DEFAULT_MESSAGE_TEMPLATE = dedent(
    """\
    番剧名称：{official_title}
    季度：第{season}季
    更新集数：第{episode}集
    {poster_path}
    """
)

DEFAULT_LOG_TEMPLATE = dedent(
    """\
    日志时间：{dt}
    日志等级：{levelname}
    日志消息：{msg}
    """
)


class NotifierAdapter(BaseModel, ABC):
    """NotifierAdapter is a common class for specific notification service."""

    template: str = Field(DEFAULT_MESSAGE_TEMPLATE, description="message template")

    @abstractmethod
    def send(self, *args, **kwargs):
        raise NotImplementedError("send method is not implemented yet.")


_Mapping = Dict[str, Any]


class NotifierRequestMixin:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(5),
        after=after_log(logger, logging.ERROR),
    )
    async def asend(
        self,
        entrypoint: str,
        base_url: Optional[str] = None,
        method: Literal["GET", "POST"] = "GET",
        data: Optional[_Mapping] = None,
        params: Optional[_Mapping] = None,
        headers: Optional[_Mapping] = None,
    ) -> Any:
        """asend is a async send method."""

        logger.debug(
            f"asend info: entrypoint={entrypoint}, "
            f"base_url={base_url}, "
            f"method={method}, "
            f"data={data}, "
            f"params={params}, "
            f"headers={headers}"
        )

        async with aiohttp.ClientSession(base_url=base_url) as req:
            resp: aiohttp.ClientResponse = await req.request(
                method, entrypoint, data=data, params=params, headers=headers
            )

            return await resp.json()
