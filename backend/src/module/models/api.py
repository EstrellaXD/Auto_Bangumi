from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


class RssLink(BaseModel):
    rss_link: str


class AddRule(BaseModel):
    title: str
    season: int


class ChangeConfig(BaseModel):
    config: dict


class ChangeRule(BaseModel):
    rule: dict


class NotificationMessageIds(BaseModel):
    message_ids: list[str] = Field(..., description="message ids to be set read")


class NotificationData(BaseModel):
    title: str = Field("AutoBangumi", description="title of the notification")
    content: str = Field(..., description="content of the notification")
    datetime: str = Field(..., description="datetime of the notification")
    has_read: bool = Field(False, description="whether the notification has been read")
    id: str = Field(..., description="id of the notification")

    @validator("datetime", pre=True)
    def from_nanoseconds_to_datetime(cls, v: int) -> str:
        return datetime.strftime(datetime.fromtimestamp(v / 1e9), "%Y-%m-%d %H:%M:%S")


class APIResponse(BaseModel):
    code: int = Field(200, description="status of the request")
    message: str = Field(..., description="message of the request")
    data: dict[str, Any] = Field(
        default_factory=dict, description="data of the request"
    )
