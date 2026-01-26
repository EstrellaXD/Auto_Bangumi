from os.path import expandvars
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Program(BaseModel):
    rss_time: int = Field(900, description="Sleep time")
    rename_time: int = Field(60, description="Rename times in one loop")
    webui_port: int = Field(7892, description="WebUI port")


class Downloader(BaseModel):
    type: str = Field("qbittorrent", description="Downloader type")
    host_: str = Field("172.17.0.1:8080", alias="host", description="Downloader host")
    username_: str = Field("admin", alias="username", description="Downloader username")
    password_: str = Field(
        "adminadmin", alias="password", description="Downloader password"
    )
    path: str = Field("/downloads/Bangumi", description="Downloader path")
    ssl: bool = Field(False, description="Downloader ssl")

    @property
    def host(self):
        return expandvars(self.host_)

    @property
    def username(self):
        return expandvars(self.username_)

    @property
    def password(self):
        return expandvars(self.password_)


class RSSParser(BaseModel):
    enable: bool = Field(True, description="Enable RSS parser")
    filter: list[str] = Field(["720", r"\d+-\d"], description="Filter")
    language: str = "zh"


class BangumiManage(BaseModel):
    enable: bool = Field(True, description="Enable bangumi manage")
    eps_complete: bool = Field(False, description="Enable eps complete")
    rename_method: str = Field("pn", description="Rename method")
    group_tag: bool = Field(False, description="Enable group tag")
    remove_bad_torrent: bool = Field(False, description="Remove bad torrent")


class Log(BaseModel):
    debug_enable: bool = Field(False, description="Enable debug")


class Proxy(BaseModel):
    enable: bool = Field(False, description="Enable proxy")
    type: str = Field("http", description="Proxy type")
    host: str = Field("", description="Proxy host")
    port: int = Field(0, description="Proxy port")
    username_: str = Field("", alias="username", description="Proxy username")
    password_: str = Field("", alias="password", description="Proxy password")

    @property
    def username(self):
        return expandvars(self.username_)

    @property
    def password(self):
        return expandvars(self.password_)


class Notification(BaseModel):
    enable: bool = Field(False, description="Enable notification")
    type: str = Field("telegram", description="Notification type")
    token_: str = Field("", alias="token", description="Notification token")
    chat_id_: str = Field("", alias="chat_id", description="Notification chat id")

    @property
    def token(self):
        return expandvars(self.token_)

    @property
    def chat_id(self):
        return expandvars(self.chat_id_)


class ExperimentalOpenAI(BaseModel):
    enable: bool = Field(False, description="Enable experimental OpenAI")
    api_key: str = Field("", description="OpenAI api key")
    api_base: str = Field(
        "https://api.openai.com/v1", description="OpenAI api base url"
    )
    api_type: Literal["azure", "openai"] = Field(
        "openai", description="OpenAI api type, usually for azure"
    )
    api_version: str = Field(
        "2023-05-15", description="OpenAI api version, only for Azure"
    )
    model: str = Field(
        "gpt-3.5-turbo", description="OpenAI model, ignored when api type is azure"
    )
    deployment_id: str = Field(
        "", description="Azure OpenAI deployment id, ignored when api type is openai"
    )

    @field_validator("api_base")
    @classmethod
    def validate_api_base(cls, value: str) -> str:
        if value == "https://api.openai.com/":
            return "https://api.openai.com/v1"
        return value


class Config(BaseModel):
    program: Program = Program()
    downloader: Downloader = Downloader()
    rss_parser: RSSParser = RSSParser()
    bangumi_manage: BangumiManage = BangumiManage()
    log: Log = Log()
    proxy: Proxy = Proxy()
    notification: Notification = Notification()
    experimental_openai: ExperimentalOpenAI = ExperimentalOpenAI()

    def model_dump(self, *args, by_alias=True, **kwargs):
        return super().model_dump(*args, by_alias=by_alias, **kwargs)

    # Keep dict() for backward compatibility
    def dict(self, *args, by_alias=True, **kwargs):
        return self.model_dump(*args, by_alias=by_alias, **kwargs)
