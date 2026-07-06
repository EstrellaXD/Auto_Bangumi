"""多提供商 LLM 标题解析器（门面）。

具体提供商逻辑在 ``providers/`` 包中（内置 openai/anthropic/gemini 适配器
+ 注册表）；本模块保留三样东西以维持既有 patch/import 路径：

- ``_build_http_client``：代理感知的 httpx 客户端工厂（测试 patch
  ``module.parser.analyser.llm.httpx`` / ``AsyncProxyTransport``）；
- ``Episode``/``EPISODE_JSON_SCHEMA``/``DEFAULT_PROMPT`` 等共享契约的
  重导出（物理定义在 providers/schema.py）；
- ``LLMParser``：构造签名不变的薄门面，将 ``_openai_client`` 等内部
  客户端属性双向委托给适配器（测试直接改写/重绑这些属性）。
"""

import logging
from typing import Any

import httpx
from httpx_socks import AsyncProxyTransport

from module.conf import settings

from .providers.base import AdapterContext
from .providers.credentials import CredentialStore
from .providers.registry import registry
from .providers.schema import (  # noqa: F401  (re-exported for existing importers)
    DEFAULT_PROMPT,
    EPISODE_JSON_SCHEMA,
    GEMINI_JSON_INSTRUCTION,
    Episode,
)

logger = logging.getLogger(__name__)

# 测试通过这些属性名直接操作/重绑底层 SDK 客户端；门面把它们的读写
# 都转发给适配器实例。
_ADAPTER_ATTRS = frozenset(
    {"_openai_client", "_anthropic_client", "_gemini_client", "_http_client"}
)


class LLMParser:
    """按 provider 分发的 LLM 标题解析器（适配器门面）。"""

    def __init__(
        self,
        api_key: str,
        provider: str = "openai",
        model: str = "gpt-5-mini",
        base_url: str = "",
        timeout: float = 20.0,
    ) -> None:
        """初始化解析器并构建对应提供商的适配器。

        Args:
            api_key: 提供商 API 密钥（api_key 类提供商必填）。
            provider: 注册表中的提供商 id。
            model: 模型名。
            base_url: 自定义端点；空串表示官方 API。
            timeout: 单次 LLM 请求超时秒数。

        Raises:
            ValueError: api_key 为空（api_key 类提供商）或 provider 不受支持。
        """
        adapter_cls = registry.resolve(provider)
        if adapter_cls.info.auth_kind == "api_key" and not api_key:
            raise ValueError("API key is required.")
        self.provider = provider
        self.model = model
        self._adapter = adapter_cls(
            AdapterContext(
                model=model,
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                build_http_client=_build_http_client,
                # 订阅类适配器 parse/list_models 时读取凭据；api_key 类忽略。
                credentials=CredentialStore(provider),
            )
        )

    def __getattr__(self, name: str) -> Any:
        # 仅在常规查找失败时触发：把适配器持有的客户端属性透出。
        return getattr(object.__getattribute__(self, "_adapter"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in _ADAPTER_ATTRS:
            setattr(self._adapter, name, value)
        else:
            object.__setattr__(self, name, value)

    async def aclose(self) -> None:
        await self._adapter.aclose()

    async def list_models(self) -> list[str]:
        """列出当前提供商可用的模型 id（升序）。SDK 异常原样抛出。"""
        return await self._adapter.list_models()

    async def parse(self, raw: str, asdict: bool = True) -> dict | None:
        """解析种子标题，返回 Episode 形状的 dict；失败返回 None。

        Args:
            raw: 待解析的原始标题。
            asdict: 保留的兼容参数，结果始终为 dict（或 None）。
        """
        result = await self._adapter.parse(raw)
        logger.debug("LLM(%s) parsed result: %s", self.provider, result)
        return result


def _build_http_client(timeout: float) -> httpx.AsyncClient:
    http_timeout = httpx.Timeout(
        connect=min(timeout, 10.0),
        read=timeout,
        write=min(timeout, 10.0),
        pool=min(timeout, 10.0),
    )
    kwargs: dict[str, Any] = {"timeout": http_timeout, "follow_redirects": True}
    if not settings.proxy.enable:
        return httpx.AsyncClient(**kwargs)
    if "http" in settings.proxy.type:
        if settings.proxy.username:
            proxy_url = (
                f"http://{settings.proxy.username}:{settings.proxy.password}"
                f"@{settings.proxy.host}:{settings.proxy.port}"
            )
        else:
            proxy_url = f"http://{settings.proxy.host}:{settings.proxy.port}"
        return httpx.AsyncClient(proxy=proxy_url, **kwargs)
    if settings.proxy.type == "socks5":
        if settings.proxy.username:
            proxy_url = (
                f"socks5://{settings.proxy.username}:{settings.proxy.password}"
                f"@{settings.proxy.host}:{settings.proxy.port}"
            )
        else:
            proxy_url = f"socks5://{settings.proxy.host}:{settings.proxy.port}"
        return httpx.AsyncClient(
            transport=AsyncProxyTransport.from_url(proxy_url, rdns=True), **kwargs
        )
    return httpx.AsyncClient(**kwargs)
