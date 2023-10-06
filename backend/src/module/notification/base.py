from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

DEFAULT_MESSAGE_TEMPLATE = """\
番剧名称：{official_title}\n季度：第{season}季\n更新集数：第{episode}集\n{poster_path}
"""


class NotifierAdapter(BaseModel, ABC):
    """NotifierAdapter is a common class for specific notification service."""

    template: str = Field(DEFAULT_MESSAGE_TEMPLATE, description="message template")

    @abstractmethod
    def send(self, *args, **kwargs):
        raise NotImplementedError("send method is not implemented yet.")
