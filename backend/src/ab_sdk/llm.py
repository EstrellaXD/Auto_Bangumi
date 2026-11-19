"""LLM 提供商适配器契约。

第三方 LLM 插件用 ``@provider(points.LLM_PROVIDER, id=...)`` 返回一个
:class:`LLMProviderAdapter` 子类（provider id 须与 ``info.id`` 一致）；用户在
LLM 设置里选择该 id 即可使用。

一个提供商 = 一个 `LLMProviderAdapter` 子类：负责客户端构造、
`parse`/`list_models`，以及（订阅类提供商）认证流程钩子。内置三家与
国产预设走 api_key；订阅插件（device_code/oauth）另行实现认证钩子。
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, Optional

import httpx2
from pydantic import BaseModel


class ProviderInfo(BaseModel):
    """提供商静态描述，驱动前端表单与注册表列举。"""

    id: str
    display_name: str
    auth_kind: Literal["api_key", "oauth", "device_code"] = "api_key"
    builtin: bool = False
    needs_base_url: bool = False
    preset_base_url: str = ""
    default_model: str = ""
    # OpenAI 兼容端点是否支持 json_schema 结构化输出；False 时降级为
    # json_object + schema 写入提示词（DeepSeek/MiniMax）。
    supports_json_schema: bool = True
    plugin_version: str | None = None


class AuthChallenge(BaseModel):
    """begin_auth 的产物：引导用户完成授权所需的全部信息。"""

    method: Literal["redirect_paste", "device_code"]
    authorize_url: str | None = None
    user_code: str | None = None
    verification_uri: str | None = None
    expires_in: int = 600
    state: str


class TokenSet(BaseModel):
    """一次成功认证得到的凭据集（服务端持久化，永不下发前端）。"""

    access_token: str
    refresh_token: str = ""
    expires_at: float | None = None  # epoch 秒
    account_label: str = ""
    extra: dict = {}


class AuthExpiredError(Exception):
    """凭据失效且刷新失败——调用方应立即熔断并通知用户重新连接。"""


def _http_client_not_injected(timeout: float) -> httpx2.AsyncClient:
    raise RuntimeError("AdapterContext.build_http_client 未注入")


@dataclass
class AdapterContext:
    """适配器可触达的全部依赖（除此之外不读全局配置）。"""

    model: str
    api_key: str = ""
    base_url: str = ""
    timeout: float = 20.0
    # llm._build_http_client——代理感知的 httpx2 客户端工厂（保持其
    # patch 路径在 llm.py，因此以依赖注入方式传入）。
    build_http_client: Callable[[float], httpx2.AsyncClient] = field(
        default=_http_client_not_injected
    )
    # M3 起为 CredentialStore；api_key 类适配器恒为 None。
    credentials: Any = None


class LLMProviderAdapter(ABC):
    """提供商适配器基类。"""

    info: ClassVar[ProviderInfo]

    _http_client: httpx2.AsyncClient | None = None

    def __init__(self, ctx: AdapterContext) -> None:
        self.ctx = ctx
        # 模型留空时回退到本提供商的默认型号（预设/插件各有自己的默认，
        # 不会误用 openai 的 gpt-5-mini）。
        self.model = ctx.model or self.info.default_model

    @abstractmethod
    async def parse(self, raw: str) -> dict | None:
        """解析种子标题为 Episode 形状 dict；失败返回 None。"""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """列出可用模型 id（升序）。"""

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()

    # ------------------------------------------------------------ auth hooks
    # 仅 oauth / device_code 适配器覆写；api_key 类默认不支持。

    async def begin_auth(self) -> AuthChallenge:
        raise NotImplementedError(f"{self.info.id} does not support interactive auth")

    async def complete_auth(self, state: str, user_input: str = "") -> TokenSet:
        raise NotImplementedError(f"{self.info.id} does not support interactive auth")

    async def refresh(self, tokens: TokenSet) -> TokenSet:
        raise NotImplementedError(f"{self.info.id} does not support token refresh")

    async def revoke(self, tokens: TokenSet) -> None:  # noqa: B027 默认无操作，子类按需覆盖
        """注销远端凭据，尽力而为；默认无操作。"""
