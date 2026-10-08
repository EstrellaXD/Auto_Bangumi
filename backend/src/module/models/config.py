from dataclasses import dataclass
from os.path import expandvars
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ab_sdk.rename import CORE_ID


def _expand(value: str | None) -> str:
    """Expand shell environment variables in *value*, returning empty string for None."""
    return expandvars(value) if value else ""


class Program(BaseModel):
    """Scheduler timing and WebUI port settings."""

    rss_time: int = Field(default=900, description="Sleep time")
    rename_time: int = Field(default=60, description="Rename times in one loop")
    webui_port: int = Field(default=7892, description="WebUI port")


class DownloaderOptions(BaseModel):
    """下载器实例的连接参数（``plugins.instances`` 中 point 为 downloader 的 options）。

    ``host`` / ``username`` / ``password`` 以带下划线的字段存储，通过属性读取，
    读取时展开 ``$VAR`` 环境变量引用。
    """

    host_: str = Field(
        default="172.17.0.1:8080", alias="host", description="Downloader host"
    )
    username_: str = Field(
        default="admin", alias="username", description="Downloader username"
    )
    # 等同 ab_sdk.secret_field()；直接写 Field 以便 mypy 识别别名
    password_: str = Field(
        default="adminadmin",
        alias="password",
        description="Downloader password",
        json_schema_extra={"secret": True},
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


@dataclass(frozen=True)
class DownloaderInstance:
    """一个下载器实例的只读视图（``type`` 即 Provider id），变量已展开。"""

    id: str
    type: str
    host: str
    username: str
    password: str
    path: str
    ssl: bool


class RSSParser(BaseModel):
    """RSS feed parsing settings."""

    enable: bool = Field(default=True, description="Enable RSS parser")
    filter: list[str] = Field(default=["720", r"\d+-\d+"], description="Filter")
    language: str = "zh"
    engine: Literal["classic", "tokenizer"] = Field(
        default="classic",
        description="Title parser engine (classic or tokenizer Preview)",
    )


class BangumiManage(BaseModel):
    """File organisation and renaming settings."""

    enable: bool = Field(default=True, description="Enable bangumi manage")
    eps_complete: bool = Field(default=False, description="Enable eps complete")
    group_tag: bool = Field(default=False, description="Enable group tag")
    remove_bad_torrent: bool = Field(default=False, description="Remove bad torrent")
    # 关闭后 refresh_rss 不再把未匹配种子入库（孤儿记录）；代价是这些条目
    # 每轮会被重新内存匹配（廉价），好处是后补规则能立即接住仍在源里的旧集
    track_orphans: bool = Field(
        default=True, description="Persist unmatched (orphan) torrents"
    )


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
    # 留空时回退到内置共享 key；自配 key 可避开共享 key 的限流 (#975)
    tmdb_api_key: str = Field(default="", description="Custom TMDB API key")
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

    # 插件提供的渠道可以携带自己的字段（作为 NotifierSettings.extra 传给插件），
    # 保留未知字段以免保存配置时被丢弃
    model_config = ConfigDict(extra="allow")

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


class LLMProviderOverride(BaseModel):
    """单个提供商的凭据/模型/端点覆盖（键名含 api_key，掩码机制自动生效）。"""

    api_key: str = Field(default="", description="Provider API key")
    model: str = Field(default="", description="Model override")
    base_url: str = Field(default="", description="Base URL override")


class LLM(BaseModel):
    """LLM 标题解析配置，支持多提供商。

    ``provider="openai"`` 表示任意 OpenAI 兼容端点（DeepSeek/Ollama/
    LM Studio/OpenRouter/OneAPI 等均可通过 ``base_url`` 接入）。
    扁平的 ``api_key/model/base_url`` 是历史字段（老用户零迁移）；
    ``providers`` 按提供商 id 存放各自的覆盖值，取值见 ``effective()``。
    """

    enable: bool = Field(default=False, description="Enable LLM parser")
    # 开放为任意注册表 id：内置三家 + base_url 预设 + 已安装插件
    provider: str = Field(default="openai", min_length=1, description="LLM provider id")
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
    providers: dict[str, LLMProviderOverride] = Field(
        default_factory=dict,
        description="Per-provider overrides keyed by provider id",
    )

    def effective(self, provider_id: str | None = None) -> tuple[str, str, str]:
        """返回 (api_key, model, base_url)。

        有 providers[id] 覆盖项时用其值（可为空，交由适配器回退到该提供商
        自己的默认端点/型号）；不跨提供商回退到扁平的 openai 字段——否则
        DeepSeek 等会误收到 openai 的 model/base_url。仅当无覆盖项（内置
        openai 默认路径）才用扁平字段。
        """
        pid = provider_id or self.provider
        override = self.providers.get(pid)
        if override is None:
            return self.api_key, self.model, self.base_url
        return override.api_key, override.model, override.base_url


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
    ``auto_check`` 控制自动检查更新：前端进入设置页时检查一次，
    后端每 24 小时检查一次并把新版本写入通知中心。
    """

    channel: Literal["stable", "beta"] = Field(
        default="stable", description="Update channel"
    )
    auto_check: bool = Field(default=True, description="Auto-check for updates")


DOWNLOADER_POINT = "downloader"
DEFAULT_DOWNLOADER_ID = "default"


class PluginInstance(BaseModel):
    """多实例扩展点（目前只有下载器）的一个实例：用 ``provider`` 实现，``options``
    为该实现的配置。秘密字段按 ``secret_field`` 规则掩码。"""

    id: str = Field(min_length=1, description="Instance id")
    point: str = Field(description="Extension point")
    provider: str = Field(description="Provider id")
    options: dict[str, Any] = Field(default_factory=dict)


def _default_instances() -> list[PluginInstance]:
    return [
        PluginInstance(
            id=DEFAULT_DOWNLOADER_ID,
            point=DOWNLOADER_POINT,
            provider="qbittorrent",
            options=DownloaderOptions().model_dump(by_alias=True),
        )
    ]


class Slots(BaseModel):
    """Provider 选择：扩展点 → Provider id；下载器选的是实例 id。"""

    downloader: str = Field(
        default=DEFAULT_DOWNLOADER_ID, description="Default downloader instance id"
    )
    rename_strategy: str = Field(default="pn", description="Rename method")
    # 内置的 hold / replace 只在新种子是唯一占用者的严格版本升级时才可能替换
    conflict_policy: str = Field(
        default="hold",
        description="How to handle a higher revision targeting an existing episode",
    )
    media_files: str = Field(default=CORE_ID, description="Media file classifier")


class Plugins(BaseModel):
    """插件系统配置。

    启用状态缺省时：内置插件启用，其它来源的插件禁用。本地目录与 pip 安装的
    插件未经签名，必须先开启 ``allow_unsigned`` 才能加载。
    """

    allow_unsigned: bool = Field(
        default=False, description="Allow loading unsigned (local / pip) plugins"
    )
    enabled: dict[str, bool] = Field(
        default_factory=dict, description="Per-plugin enable switch, keyed by id"
    )
    options: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Per-plugin options, keyed by id"
    )
    hook_order: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Explicit hook order per extension point (plugin ids)",
    )
    slots: Slots = Field(default_factory=Slots)
    instances: list[PluginInstance] = Field(default_factory=_default_instances)

    @model_validator(mode="after")
    def _check_instances(self) -> "Plugins":
        ids = [i.id for i in self.instances]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate plugin instance id in {ids}")
        for instance in self.instances:
            if instance.point == DOWNLOADER_POINT:
                DownloaderOptions.model_validate(instance.options)
        if not any(
            i.id == self.slots.downloader and i.point == DOWNLOADER_POINT
            for i in self.instances
        ):
            raise ValueError(
                f"slots.downloader {self.slots.downloader!r} "
                "is not a downloader instance"
            )
        return self


class Config(BaseModel):
    """Root configuration model composed of all subsection models."""

    program: Program = Program()
    rss_parser: RSSParser = RSSParser()
    bangumi_manage: BangumiManage = BangumiManage()
    log: Log = Log()
    network: Network = Network()
    proxy: Proxy = Proxy()
    notification: Notification = Notification()
    llm: LLM = LLM()
    security: Security = Security()
    update: Update = Update()
    plugins: Plugins = Plugins()

    @property
    def downloader(self) -> DownloaderInstance:
        """默认下载器实例（``plugins.slots.downloader``）。"""
        return self.downloader_instance(self.plugins.slots.downloader)

    def downloader_instance(self, instance_id: str) -> DownloaderInstance:
        instance = next(
            (
                i
                for i in self.plugins.instances
                if i.id == instance_id and i.point == DOWNLOADER_POINT
            ),
            None,
        )
        if instance is None:
            raise KeyError(f"unknown downloader instance {instance_id!r}")
        options = DownloaderOptions.model_validate(instance.options)
        return DownloaderInstance(
            id=instance.id,
            type=instance.provider,
            host=options.host,
            username=options.username,
            password=options.password,
            path=options.path,
            ssl=options.ssl,
        )

    def model_dump(self, *args, by_alias=True, **kwargs):
        return super().model_dump(*args, by_alias=by_alias, **kwargs)

    # Keep dict() for backward compatibility
    def dict(self, *args, by_alias=True, **kwargs):
        return self.model_dump(*args, by_alias=by_alias, **kwargs)
