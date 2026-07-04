"""多提供商 LLM 标题解析器。

支持三类提供商：
- ``openai``：任意 OpenAI 兼容端点（官方 API、DeepSeek、Ollama、
  LM Studio、OpenRouter、OneAPI 等，经 ``base_url`` 接入）
- ``anthropic``：Anthropic Claude
- ``gemini``：Google Gemini

各提供商的 ``parse()`` 返回统一的 Episode 形状 dict；任何 API 错误、
拒答或输出不可解析时返回 None，由调用方（title_parser）决定回退策略。
"""

import json
import logging
from typing import Any, Optional

import httpx
from httpx_socks import AsyncProxyTransport
from pydantic import BaseModel

from module.conf import settings

# anthropic / openai / google-genai 合计导入约 0.7s，而 LLM 默认关闭。
# 这些重型 SDK 改为在真正构造/调用某提供商时才导入（见 __init__ 与各
# _parse_* 方法），把这段耗时移出容器启动路径。httpx / httpx_socks 保持
# 顶层导入：它们本就在网络层被加载，且测试按模块级名字 patch 它们。

logger = logging.getLogger(__name__)


class Episode(BaseModel):
    """LLM 结构化输出的目标形状（与 models.bangumi.Episode 字段一致）。"""

    title_en: Optional[str]
    title_zh: Optional[str]
    title_jp: Optional[str]
    season: int
    season_raw: str
    episode: int
    sub: str
    group: str
    resolution: str
    source: str


# Anthropic 结构化输出要求：所有属性均列入 required，
# additionalProperties 为 false，且不带 min/max 等约束
EPISODE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title_en": {"type": ["string", "null"]},
        "title_zh": {"type": ["string", "null"]},
        "title_jp": {"type": ["string", "null"]},
        "season": {"type": "integer"},
        "season_raw": {"type": "string"},
        "episode": {"type": "integer"},
        "sub": {"type": "string"},
        "group": {"type": "string"},
        "resolution": {"type": "string"},
        "source": {"type": "string"},
    },
    "required": [
        "title_en",
        "title_zh",
        "title_jp",
        "season",
        "season_raw",
        "episode",
        "sub",
        "group",
        "resolution",
        "source",
    ],
    "additionalProperties": False,
}


DEFAULT_PROMPT = """\
You will now play the role of a super assistant.
Your task is to extract structured data from unstructured text content and output it in JSON format.
If you are unable to extract any information, please keep all fields and leave the field empty or default value like `''`, `None`.
But Do not fabricate data!
"""

# Gemini 走 response_mime_type + 提示词描述 JSON 形状（避免 SDK schema
# 类型与 mypy 冲突），因此在提示词里显式给出字段列表
GEMINI_JSON_INSTRUCTION = (
    "Output a single JSON object with exactly these keys: "
    "title_en (string or null), title_zh (string or null), "
    "title_jp (string or null), season (integer), season_raw (string), "
    "episode (integer), sub (string), group (string), "
    "resolution (string), source (string)."
)


class LLMParser:
    """按 provider 分发的 LLM 标题解析器。"""

    def __init__(
        self,
        api_key: str,
        provider: str = "openai",
        model: str = "gpt-5-mini",
        base_url: str = "",
        timeout: float = 20.0,
    ) -> None:
        """初始化解析器并构建对应提供商的异步客户端。

        Args:
            api_key: 提供商 API 密钥，必填。
            provider: "openai" | "anthropic" | "gemini"。
            model: 模型名。
            base_url: 自定义端点，仅 openai 提供商使用；空串表示官方 API。
            timeout: 单次 LLM 请求超时秒数。

        Raises:
            ValueError: api_key 为空或 provider 不受支持。
        """
        if not api_key:
            raise ValueError("API key is required.")
        self.provider = provider
        self.model = model
        self._http_client: httpx.AsyncClient | None = None
        if provider == "openai":
            from openai import AsyncOpenAI

            self._http_client = _build_http_client(timeout)
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or None,
                timeout=timeout,
                http_client=self._http_client,
            )
        elif provider == "anthropic":
            import anthropic

            self._http_client = _build_http_client(timeout)
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=api_key,
                timeout=timeout,
                http_client=self._http_client,
            )
        elif provider == "gemini":
            from google import genai

            self._gemini_client = genai.Client(api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()

    async def list_models(self) -> list[str]:
        """列出当前提供商可用的模型 id（升序）。

        openai 走 ``/models``（自定义 base_url 时即该端点的模型表）；
        gemini 只保留支持 generateContent 的模型并去掉 ``models/`` 前缀。
        SDK 异常原样抛出，由调用方决定如何呈现。
        """
        ids: list[str]
        if self.provider == "openai":
            openai_page = await self._openai_client.models.list()
            ids = [m.id for m in openai_page.data]
        elif self.provider == "anthropic":
            anthropic_page = await self._anthropic_client.models.list()
            ids = [m.id for m in anthropic_page.data]
        else:
            ids = []
            async for m in await self._gemini_client.aio.models.list():
                actions = getattr(m, "supported_actions", None)
                if actions and "generateContent" not in actions:
                    continue
                name = m.name or ""
                ids.append(name.removeprefix("models/"))
        return sorted(ids)

    async def parse(self, raw: str, asdict: bool = True) -> dict | None:
        """解析种子标题，返回 Episode 形状的 dict；失败返回 None。

        Args:
            raw: 待解析的原始标题。
            asdict: 保留的兼容参数，结果始终为 dict（或 None）。
        """
        if self.provider == "openai":
            result = await self._parse_openai(raw)
        elif self.provider == "anthropic":
            result = await self._parse_anthropic(raw)
        else:
            result = await self._parse_gemini(raw)
        logger.debug("LLM(%s) parsed result: %s", self.provider, result)
        return result

    async def _parse_openai(self, raw: str) -> dict | None:
        import openai as openai_sdk

        try:
            resp = await self._openai_client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": DEFAULT_PROMPT},
                    {"role": "user", "content": raw},
                ],
                response_format=Episode,
                # temperature 置 0，让结果更稳定可复现
                temperature=0,
            )
            parsed = resp.choices[0].message.parsed
        except openai_sdk.OpenAIError as e:
            logger.warning("OpenAI parse failed for '%s': %s", raw, e)
            return None
        if parsed is None:
            logger.warning("OpenAI returned no parsed content for '%s'", raw)
            return None
        return parsed.model_dump()

    async def _parse_anthropic(self, raw: str) -> dict | None:
        import anthropic

        try:
            resp = await self._anthropic_client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=DEFAULT_PROMPT,
                messages=[{"role": "user", "content": raw}],
                output_config={
                    "format": {"type": "json_schema", "schema": EPISODE_JSON_SCHEMA}
                },
            )
        except (
            anthropic.RateLimitError,
            anthropic.APIStatusError,
            anthropic.APIConnectionError,
        ) as e:
            logger.warning("Anthropic parse failed for '%s': %s", raw, e)
            return None
        if resp.stop_reason == "refusal":
            logger.warning("Anthropic refused to parse '%s'", raw)
            return None
        try:
            text = next(b.text for b in resp.content if b.type == "text")
            return json.loads(text)
        except (StopIteration, json.JSONDecodeError) as e:
            logger.warning("Cannot decode Anthropic output for '%s': %s", raw, e)
            return None

    async def _parse_gemini(self, raw: str) -> dict | None:
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types

        try:
            resp = await self._gemini_client.aio.models.generate_content(
                model=self.model,
                contents=f"{DEFAULT_PROMPT}\n{GEMINI_JSON_INSTRUCTION}\n\n{raw}",
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            text = resp.text
        except genai_errors.APIError as e:
            logger.warning("Gemini parse failed for '%s': %s", raw, e)
            return None
        if not text:
            logger.warning("Gemini returned no text for '%s'", raw)
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Cannot decode Gemini output for '%s': %s", raw, e)
            return None


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
