from pydantic import BaseModel, Field


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
