from pydantic import BaseModel


class RssLink(BaseModel):
    rss_link: str


class AddRule(BaseModel):
    title: str
    season: int


class ChangeConfig(BaseModel):
    config: dict


class ChangeRule(BaseModel):
    rule: dict

