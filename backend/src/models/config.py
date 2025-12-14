from typing import Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T", bound=BaseSettings)


class Program(BaseSettings):
    # rss_time must be greater than 300,if less than 300,it will be set to 300
    rss_time: int = Field(default=900, description="Sleep time")
    webui_port: int = Field(default=7892, description="WebUI port")
    dev_mode: bool = Field(default=False, description="Enable dev mode")
    model_config = SettingsConfigDict(
        env_prefix='AB_PROGRAM__',
        case_sensitive=False,
        extra='ignore',
    )

    @model_validator(mode="after")
    def validate_rss_time(self) -> Self:
        self.rss_time = max(self.rss_time, 300)
        return self


class Downloader(BaseSettings):
    type: str = Field(default="qbittorrent", description="Downloader type")
    path: str = Field(default="/downloads/Bangumi", description="Downloader path")
    host: str = Field(default="172.17.0.1:8080", alias="host", description="Downloader host")
    username: str = Field(default="admin", alias="username", description="Downloader username")
    password: str = Field(default="adminadmin", alias="password", description="Downloader password")
    ssl: bool = Field(default=False, description="Downloader ssl")

    model_config = SettingsConfigDict(
        env_prefix='AB_DOWNLOADER__',
        case_sensitive=False,
        extra='ignore',
    )

    @model_validator(mode="after")
    def validate_host(self) -> Self:
        # 如果输入值没有以 http:// 或 https:// 开头，自动加上 http://
        if not self.host.startswith(("http://", "https://")):
            self.host = f"http://{self.host}"
        return self


class RSSParser(BaseSettings):
    enable: bool = Field(default=True, description="Enable RSS parser")
    filter: list[str] = Field(default=["720", r"\d+-\d"], description="Filter")
    include: list[str] = Field(default=[], description="Include")
    language: str = "zh"
    mikan_custom_url: str = Field(default="mikanani.me", description="Mikan custom url")
    tmdb_api_key: str = Field(
        default="",
        description="TMDB API key, used for TMDB integration",
    )

    model_config = SettingsConfigDict(
        env_prefix='AB_RSS_PARSER__',
        case_sensitive=False,
        extra='ignore',
    )


class BangumiManage(BaseSettings):
    enable: bool = Field(default=True, description="Enable bangumi manage")
    eps_complete: bool = Field(default=False, description="Enable eps complete")
    rename_method: str = Field(default="pn", description="Rename method")
    group_tag: bool = Field(default=False, description="Enable group tag")
    remove_bad_torrent: bool = Field(default=False, description="Remove bad torrent")

    model_config = SettingsConfigDict(
        env_prefix='AB_BANGUMI_MANAGE__',
        case_sensitive=False,
        extra='ignore',
    )


class Log(BaseSettings):
    debug_enable: bool = Field(default=False, description="Enable debug")

    model_config = SettingsConfigDict(
        env_prefix='AB_LOG__',
        case_sensitive=False,
        extra='ignore',
    )


class Proxy(BaseSettings):
    enable: bool = Field(default=False, description="Enable proxy")
    type: str = Field(default="http", description="Proxy type")
    host: str = Field(default="", description="Proxy host")
    port: int = Field(default=0, description="Proxy port")
    username: str = Field(default="", alias="username", description="Proxy username")
    password: str = Field(default="", alias="password", description="Proxy password")

    model_config = SettingsConfigDict(
        env_prefix='AB_PROXY__',
        case_sensitive=False,
        extra='ignore',
    )


class Notification(BaseSettings):
    enable: bool = Field(default=False, description="Enable notification")
    type: str = Field(default="telegram", description="Notification type")
    token: str = Field(default="", alias="token", description="Notification token")
    chat_id: str = Field(default="", alias="chat_id", description="Notification chat id")

    model_config = SettingsConfigDict(
        env_prefix='AB_NOTIFICATION__',
        case_sensitive=False,
        extra='ignore',
    )


