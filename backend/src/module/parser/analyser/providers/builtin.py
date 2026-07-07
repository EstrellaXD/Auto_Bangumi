"""内置三家提供商适配器（openai / anthropic / gemini，API-Key 直连）。

解析与客户端构造逻辑自 LLMParser 原样搬入；重型 SDK 仍然懒导入
（LLM 默认关闭，导入 ~0.7s 不应进启动路径）。
"""

import json
import logging

from .base import AdapterContext, LLMProviderAdapter, ProviderInfo
from .schema import (
    DEFAULT_PROMPT,
    EPISODE_JSON_SCHEMA,
    GEMINI_JSON_INSTRUCTION,
    Episode,
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMProviderAdapter):
    """任意 OpenAI 兼容端点（官方 API、DeepSeek、Ollama、OneAPI 等）。"""

    info = ProviderInfo(
        id="openai",
        display_name="OpenAI",
        auth_kind="api_key",
        builtin=True,
        needs_base_url=True,
        default_model="gpt-5-mini",
    )

    def __init__(self, ctx: AdapterContext) -> None:
        super().__init__(ctx)
        from openai import AsyncOpenAI

        self._http_client = ctx.build_http_client(ctx.timeout)
        self._openai_client = AsyncOpenAI(
            api_key=ctx.api_key,
            # 配置留空时回退到预设端点（国产提供商预设子类）
            base_url=ctx.base_url or self.info.preset_base_url or None,
            timeout=ctx.timeout,
            http_client=self._http_client,
        )

    async def parse(self, raw: str) -> dict | None:
        if not self.info.supports_json_schema:
            return await self._parse_json_object(raw)
        return await self._parse_structured(raw)

    async def _parse_structured(self, raw: str) -> dict | None:
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

    async def _parse_json_object(self, raw: str) -> dict | None:
        """json_object 模式：schema 写入提示词，响应本地校验为 Episode。"""
        import openai as openai_sdk
        from pydantic import ValidationError

        try:
            resp = await self._openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"{DEFAULT_PROMPT}\n{GEMINI_JSON_INSTRUCTION}",
                    },
                    {"role": "user", "content": raw},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = resp.choices[0].message.content
        except openai_sdk.OpenAIError as e:
            logger.warning("OpenAI-compatible parse failed for '%s': %s", raw, e)
            return None
        if not content:
            logger.warning("OpenAI-compatible returned no content for '%s'", raw)
            return None
        try:
            return Episode(**json.loads(content)).model_dump()
        except (json.JSONDecodeError, TypeError, ValidationError) as e:
            logger.warning(
                "Cannot decode OpenAI-compatible output for '%s': %s", raw, e
            )
            return None

    async def list_models(self) -> list[str]:
        openai_page = await self._openai_client.models.list()
        return sorted(m.id for m in openai_page.data)


class AnthropicAdapter(LLMProviderAdapter):
    """Anthropic Claude（官方 API Key）。"""

    info = ProviderInfo(
        id="anthropic",
        display_name="Anthropic",
        auth_kind="api_key",
        builtin=True,
        default_model="claude-haiku-4-5",
    )

    def __init__(self, ctx: AdapterContext) -> None:
        super().__init__(ctx)
        import anthropic

        self._http_client = ctx.build_http_client(ctx.timeout)
        self._anthropic_client = anthropic.AsyncAnthropic(
            api_key=ctx.api_key,
            timeout=ctx.timeout,
            http_client=self._http_client,
        )

    async def parse(self, raw: str) -> dict | None:
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

    async def list_models(self) -> list[str]:
        anthropic_page = await self._anthropic_client.models.list()
        return sorted(m.id for m in anthropic_page.data)


class GeminiAdapter(LLMProviderAdapter):
    """Google Gemini（AI Studio API Key）。"""

    info = ProviderInfo(
        id="gemini",
        display_name="Google Gemini",
        auth_kind="api_key",
        builtin=True,
        default_model="gemini-2.5-flash",
    )

    def __init__(self, ctx: AdapterContext) -> None:
        super().__init__(ctx)
        from google import genai

        self._gemini_client = genai.Client(api_key=ctx.api_key)

    async def parse(self, raw: str) -> dict | None:
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

    async def list_models(self) -> list[str]:
        ids: list[str] = []
        async for m in await self._gemini_client.aio.models.list():
            actions = getattr(m, "supported_actions", None)
            if actions and "generateContent" not in actions:
                continue
            name = m.name or ""
            ids.append(name.removeprefix("models/"))
        return sorted(ids)


BUILTIN: dict[str, type[LLMProviderAdapter]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "gemini": GeminiAdapter,
}
