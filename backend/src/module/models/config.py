from os.path import expandvars
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _expand(value: str | None) -> str:
    """Expand shell environment variables in *value*, returning empty string for None."""
    return expandvars(value) if value else ""


class Program(BaseModel):
    """Scheduler timing and WebUI port settings."""

    rss_time: int = Field(default=900, description="Sleep time")
    rename_time: int = Field(default=60, description="Rename times in one loop")
    webui_port: int = Field(default=7892, description="WebUI port")


class Downloader(BaseModel):
    """Download client connection settings.

    Credential fields (``host``, ``username``, ``password``) are stored with a
    trailing underscore and exposed via properties that expand ``$VAR``
    environment variable references at access time.
    """

    type: str = Field(default="qbittorrent", description="Downloader type")
    host_: str = Field(
        default="172.17.0.1:8080", alias="host", description="Downloader host"
    )
    username_: str = Field(
        default="admin", alias="username", description="Downloader username"
    )
    password_: str = Field(
        default="adminadmin", alias="password", description="Downloader password"
    )
    path: str = Field(default="/downloads/Bangumi", description="Downloader path")
    ssl: bool = Field(default=False, description="Downloader ssl")

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

    enable: bool = Field(default=True, description="Enable RSS parser")
    filter: list[str] = Field(default=["720", r"\d+-\d+"], description="Filter")
    language: str = "zh"


class BangumiManage(BaseModel):
    """File organisation and renaming settings."""

    enable: bool = Field(default=True, description="Enable bangumi manage")
    eps_complete: bool = Field(default=False, description="Enable eps complete")
    rename_method: str = Field(default="pn", description="Rename method")
    group_tag: bool = Field(default=False, description="Enable group tag")
    remove_bad_torrent: bool = Field(default=False, description="Remove bad torrent")


class Log(BaseModel):
    """Logging verbosity settings."""

    debug_enable: bool = Field(default=False, description="Enable debug")


class Network(BaseModel):
    """External data-source base URLs.

    Overridable so users behind a GFW/mirror can point TMDB and bgm.tv at a
    reachable host (#1040, #1042). Defaults are the official endpoints.
    """

    tmdb_base_url: str = Field(
        default="https://api.themoviedb.org", description="TMDB API base URL"
    )
    bgm_base_url: str = Field(
        default="https://api.bgm.tv", description="Bangumi (bgm.tv) API base URL"
    )


class Proxy(BaseModel):
    """HTTP/SOCKS proxy settings. Credentials support ``$VAR`` expansion."""

    enable: bool = Field(default=False, description="Enable proxy")
    type: str = Field(default="http", description="Proxy type")
    host: str = Field(default="", description="Proxy host")
    port: int = Field(default=0, description="Proxy port")
    username_: str = Field(default="", alias="username", description="Proxy username")
    password_: str = Field(default="", alias="password", description="Proxy password")

    @property
    def username(self):
        return _expand(self.username_)

    @property
    def password(self):
        return _expand(self.password_)


class NotificationProvider(BaseModel):
    """Configuration for a single notification provider."""

    type: str = Field(..., description="Provider type (telegram, discord, bark, etc.)")
    enabled: bool = Field(default=True, description="Whether this provider is enabled")

    # Common fields (with env var expansion)
    token_: Optional[str] = Field(default=None, alias="token", description="Auth token")
    chat_id_: Optional[str] = Field(
        default=None, alias="chat_id", description="Chat/channel ID"
    )

    # Provider-specific fields
    webhook_url_: Optional[str] = Field(
        default=None, alias="webhook_url", description="Webhook URL for discord/wecom"
    )
    server_url_: Optional[str] = Field(
        default=None, alias="server_url", description="Server URL for gotify/bark"
    )
    device_key_: Optional[str] = Field(
        default=None, alias="device_key", description="Device key for bark"
    )
    user_key_: Optional[str] = Field(
        default=None, alias="user_key", description="User key for pushover"
    )
    api_token_: Optional[str] = Field(
        default=None, alias="api_token", description="API token for pushover"
    )
    template: Optional[str] = Field(
        default=None,
        description=(
            "Custom message template ({{title}}/{{season}}/{{episode}}/"
            "{{poster_url}}); falls back to the default message when unset. "
            "Webhook renders it as JSON; other providers render it as plain "
            "text."
        ),
    )
    url_: Optional[str] = Field(
        default=None, alias="url", description="URL for generic webhook provider"
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

    enable: bool = Field(default=False, description="Enable notification system")
    providers: list[NotificationProvider] = Field(
        default_factory=list, description="List of notification providers"
    )
    base_url: str = Field(
        default="",
        description=(
            "Public base URL used to build absolute poster URLs for "
            "notification providers. Empty = omit the poster field entirely."
        ),
    )

    # Legacy fields for backward compatibility (deprecated)
    type: Optional[str] = Field(
        default=None, description="[Deprecated] Use providers instead"
    )
    token_: Optional[str] = Field(
        default=None, alias="token", description="[Deprecated]"
    )
    chat_id_: Optional[str] = Field(
        default=None, alias="chat_id", description="[Deprecated]"
    )

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


class LLM(BaseModel):
    """LLM 标题解析配置，支持多提供商。

    ``provider="openai"`` 表示任意 OpenAI 兼容端点（DeepSeek/Ollama/
    LM Studio/OpenRouter/OneAPI 等均可通过 ``base_url`` 接入）。
    """

    enable: bool = Field(default=False, description="Enable LLM parser")
    provider: Literal["openai", "anthropic", "gemini"] = Field(
        default="openai", description="LLM provider"
    )
    api_key: str = Field(default="", description="LLM api key")
    model: str = Field(default="gpt-5-mini", description="LLM model name")
    base_url: str = Field(
        default="",
        description=(
            "Custom base URL, only used by the openai provider. "
            "Empty = official API."
        ),
    )
    mode: Literal["fallback", "primary"] = Field(
        default="fallback",
        description=(
            "fallback: regex first, LLM only when regex fails; "
            "primary: LLM first, regex as safety net"
        ),
    )
    timeout: float = Field(default=20.0, ge=1.0, description="LLM request timeout")
    cache_ttl: int = Field(
        default=900,
        ge=0,
        description="Seconds to cache LLM parse successes and failures; 0 disables",
    )
    max_concurrency: int = Field(
        default=2,
        ge=1,
        description="Maximum concurrent LLM parse requests",
    )
    failure_threshold: int = Field(
        default=3,
        ge=1,
        description="Consecutive LLM failures before temporarily skipping calls",
    )
    failure_backoff: int = Field(
        default=300,
        ge=0,
        description="Seconds to skip LLM calls after failure_threshold is reached",
    )


# [Deprecated] 旧版 OpenAI 解析配置，仅保留用于读取旧配置文件（向后兼容）。
# 新配置请使用上方的 LLM 段；加载时会自动迁移（见 conf/config.py）。
class ExperimentalOpenAI(BaseModel):
    enable: bool = Field(default=False, description="Enable experimental OpenAI")
    api_key: str = Field(default="", description="OpenAI api key")
    api_base: str = Field(
        default="https://api.openai.com/v1", description="OpenAI api base url"
    )
    api_type: Literal["azure", "openai"] = Field(
        default="openai", description="OpenAI api type, usually for azure"
    )
    api_version: str = Field(
        default="2023-05-15", description="OpenAI api version, only for Azure"
    )
    model: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model, ignored when api type is azure",
    )
    deployment_id: str = Field(
        default="",
        description="Azure OpenAI deployment id, ignored when api type is openai",
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
    webauthn_rp_id: str = Field(
        default="",
        description=(
            "WebAuthn relying-party ID. Empty = derive from the request "
            "headers instead."
        ),
    )
    webauthn_origin: str = Field(
        default="",
        description=(
            "Expected WebAuthn origin. Empty = derive from the request "
            "headers instead."
        ),
    )


class Update(BaseModel):
    """在线自动更新配置。

    ``channel`` 决定检查更新时挑选稳定版还是包含预发布（beta）版本；
    ``auto_check`` 控制前端是否在进入设置页时自动检查一次更新。
    """

    channel: Literal["stable", "beta"] = Field(
        default="stable", description="Update channel"
    )
    auto_check: bool = Field(default=True, description="Auto-check for updates")


class Config(BaseModel):
    """Root configuration model composed of all subsection models."""

    program: Program = Program()
    downloader: Downloader = Downloader()
    rss_parser: RSSParser = RSSParser()
    bangumi_manage: BangumiManage = BangumiManage()
    log: Log = Log()
    network: Network = Network()
    proxy: Proxy = Proxy()
    notification: Notification = Notification()
    llm: LLM = LLM()
    # [Deprecated] 仅用于读取旧配置，运行时逻辑请读 llm 段
    experimental_openai: ExperimentalOpenAI = ExperimentalOpenAI()
    security: Security = Security()
    update: Update = Update()

    def model_dump(self, *args, by_alias=True, **kwargs):
        return super().model_dump(*args, by_alias=by_alias, **kwargs)

    # Keep dict() for backward compatibility
    def dict(self, *args, by_alias=True, **kwargs):
        return self.model_dump(*args, by_alias=by_alias, **kwargs)
