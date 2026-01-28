from os.path import expandvars
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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


class NotificationProvider(BaseModel):
    """Configuration for a single notification provider."""

    type: str = Field(..., description="Provider type (telegram, discord, bark, etc.)")
    enabled: bool = Field(True, description="Whether this provider is enabled")

    # Common fields (with env var expansion)
    token_: Optional[str] = Field(None, alias="token", description="Auth token")
    chat_id_: Optional[str] = Field(None, alias="chat_id", description="Chat/channel ID")

    # Provider-specific fields
    webhook_url_: Optional[str] = Field(
        None, alias="webhook_url", description="Webhook URL for discord/wecom"
    )
    server_url_: Optional[str] = Field(
        None, alias="server_url", description="Server URL for gotify/bark"
    )
    device_key_: Optional[str] = Field(
        None, alias="device_key", description="Device key for bark"
    )
    user_key_: Optional[str] = Field(
        None, alias="user_key", description="User key for pushover"
    )
    api_token_: Optional[str] = Field(
        None, alias="api_token", description="API token for pushover"
    )
    template: Optional[str] = Field(
        None, description="Custom template for webhook provider"
    )
    url_: Optional[str] = Field(
        None, alias="url", description="URL for generic webhook provider"
    )

    @property
    def token(self) -> str:
        return expandvars(self.token_) if self.token_ else ""

    @property
    def chat_id(self) -> str:
        return expandvars(self.chat_id_) if self.chat_id_ else ""

    @property
    def webhook_url(self) -> str:
        return expandvars(self.webhook_url_) if self.webhook_url_ else ""

    @property
    def server_url(self) -> str:
        return expandvars(self.server_url_) if self.server_url_ else ""

    @property
    def device_key(self) -> str:
        return expandvars(self.device_key_) if self.device_key_ else ""

    @property
    def user_key(self) -> str:
        return expandvars(self.user_key_) if self.user_key_ else ""

    @property
    def api_token(self) -> str:
        return expandvars(self.api_token_) if self.api_token_ else ""

    @property
    def url(self) -> str:
        return expandvars(self.url_) if self.url_ else ""


class Notification(BaseModel):
    """Notification configuration supporting multiple providers."""

    enable: bool = Field(False, description="Enable notification system")
    providers: list[NotificationProvider] = Field(
        default_factory=list, description="List of notification providers"
    )

    # Legacy fields for backward compatibility (deprecated)
    type: Optional[str] = Field(None, description="[Deprecated] Use providers instead")
    token_: Optional[str] = Field(None, alias="token", description="[Deprecated]")
    chat_id_: Optional[str] = Field(None, alias="chat_id", description="[Deprecated]")

    @property
    def token(self) -> str:
        return expandvars(self.token_) if self.token_ else ""

    @property
    def chat_id(self) -> str:
        return expandvars(self.chat_id_) if self.chat_id_ else ""

    @model_validator(mode="after")
    def migrate_legacy_config(self) -> "Notification":
        """Auto-migrate old single-provider config to new format."""
        if self.type and not self.providers:
            # Old format detected, migrate to new format
            legacy_provider = NotificationProvider(
                type=self.type,
                enabled=True,
                token=self.token_ or "",
                chat_id=self.chat_id_ or "",
            )
            self.providers = [legacy_provider]
        return self


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
