from abc import ABC, abstractmethod
from textwrap import dedent
from typing import Any, Dict, Literal, Optional, TypeAlias, TypeVar

import aiohttp
from pydantic import BaseModel, Field

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
