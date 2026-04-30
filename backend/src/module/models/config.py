from os.path import expandvars
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _expand(value: str | None) -> str:
    """Expand shell environment variables in *value*, returning empty string for None."""
    return expandvars(value) if value else ""


class Program(BaseModel):
    """Scheduler timing and WebUI port settings."""

    rss_time: int = Field(900, description="Sleep time")
    rename_time: int = Field(60, description="Rename times in one loop")
    webui_port: int = Field(7892, description="WebUI port")


class Downloader(BaseModel):
    """Download client connection settings.

    Credential fields (``host``, ``username``, ``password``) are stored with a
    trailing underscore and exposed via properties that expand ``$VAR``
    environment variable references at access time.
    """

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
        return _expand(self.host_)

    @property
    def username(self):
        return _expand(self.username_)

    @property
    def password(self):
        return _expand(self.password_)


class RSSParser(BaseModel):
    """RSS feed parsing settings."""

    enable: bool = Field(True, description="Enable RSS parser")
    filter: list[str] = Field(["720", r"\d+-\d+"], description="Filter")
    language: str = "zh"


class BangumiManage(BaseModel):
    """File organisation and renaming settings."""

    enable: bool = Field(True, description="Enable bangumi manage")
    eps_complete: bool = Field(False, description="Enable eps complete")
    rename_method: str = Field("pn", description="Rename method")
    group_tag: bool = Field(False, description="Enable group tag")
    remove_bad_torrent: bool = Field(False, description="Remove bad torrent")


class Log(BaseModel):
    """Logging verbosity settings."""

    debug_enable: bool = Field(False, description="Enable debug")


class Proxy(BaseModel):
    """HTTP/SOCKS proxy settings. Credentials support ``$VAR`` expansion."""

    enable: bool = Field(False, description="Enable proxy")
    type: str = Field("http", description="Proxy type")
    host: str = Field("", description="Proxy host")
    port: int = Field(0, description="Proxy port")
    username_: str = Field("", alias="username", description="Proxy username")
    password_: str = Field("", alias="password", description="Proxy password")

    @property
    def username(self):
        return _expand(self.username_)

    @property
    def password(self):
        return _expand(self.password_)


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
        None, alias="url", description="URL for generic webhook/onebot provider"
    )
    message_type: Optional[str] = Field(
        "private", description="Message type for onebot: 'private' or 'group'"
    )

    @property
    def token(self) -> str:
        return _expand(self.token_)

    @property
    def chat_id(self) -> str:
        return _expand(self.chat_id_)

    @property
    def webhook_url(self) -> str:
        return _expand(self.webhook_url_)

    @property
    def server_url(self) -> str:
        return _expand(self.server_url_)

    @property
    def device_key(self) -> str:
        return _expand(self.device_key_)

    @property
    def user_key(self) -> str:
        return _expand(self.user_key_)

    @property
    def api_token(self) -> str:
        return _expand(self.api_token_)

    @property
    def url(self) -> str:
        return _expand(self.url_)


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
        return _expand(self.token_)

    @property
    def chat_id(self) -> str:
        return _expand(self.chat_id_)

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


class Security(BaseModel):
    """Access control configuration for the login endpoint and MCP server.

    Both ``login_whitelist`` and ``mcp_whitelist`` accept IPv4/IPv6 CIDR ranges.
    An empty ``login_whitelist`` allows all IPs; an empty ``mcp_whitelist``
    denies all IP-based access (tokens still work).
    """

    login_whitelist: list[str] = Field(
        default_factory=list,
        description="IP/CIDR whitelist for login access. Empty = allow all.",
    )
    login_tokens: list[str] = Field(
        default_factory=list,
        description="API bearer tokens that bypass login authentication.",
    )
    mcp_whitelist: list[str] = Field(
        default_factory=list,
        description="IP/CIDR whitelist for MCP access. Empty = deny all.",
    )
    mcp_tokens: list[str] = Field(
        default_factory=list,
        description="API bearer tokens for MCP access.",
    )


class Config(BaseModel):
    """Root configuration model composed of all subsection models."""

    program: Program = Program()
    downloader: Downloader = Downloader()
    rss_parser: RSSParser = RSSParser()
    bangumi_manage: BangumiManage = BangumiManage()
    log: Log = Log()
    proxy: Proxy = Proxy()
    notification: Notification = Notification()
    experimental_openai: ExperimentalOpenAI = ExperimentalOpenAI()
    security: Security = Security()

    def model_dump(self, *args, by_alias=True, **kwargs):
        return super().model_dump(*args, by_alias=by_alias, **kwargs)

    # Keep dict() for backward compatibility
    def dict(self, *args, by_alias=True, **kwargs):
        return self.model_dump(*args, by_alias=by_alias, **kwargs)
