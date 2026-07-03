"""LLMParser 多提供商单元测试（客户端全部打桩，不发真实请求）。"""

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import anthropic
import httpx
import openai as openai_sdk
import pytest
from google.genai import errors as genai_errors

from module.parser.analyser.llm import (
    DEFAULT_PROMPT,
    EPISODE_JSON_SCHEMA,
    Episode,
    LLMParser,
)

RAW_TITLE = (
    "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
)

EPISODE_DICT: dict[str, Any] = {
    "group": "梦蓝字幕组",
    "title_en": "New Doraemon",
    "resolution": "1080P",
    "episode": 747,
    "season": 1,
    "title_zh": "哆啦A梦新番",
    "sub": "GB_JP",
    "title_jp": "",
    "season_raw": "2023.02.25",
    "source": "AVC",
}


class TestLLMParserInit:
    def test_init_without_api_key_raises(self):
        with pytest.raises(ValueError):
            LLMParser(api_key="")

    def test_init_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            LLMParser(api_key="key", provider="deepmind")


class TestOpenAIProvider:
    def _make_parser(self, **kwargs) -> LLMParser:
        return LLMParser(api_key="sk-test", provider="openai", **kwargs)

    def test_default_base_url_is_official_api(self):
        parser = self._make_parser()
        assert "api.openai.com" in str(parser._openai_client.base_url)

    def test_custom_base_url_passed_to_client(self):
        parser = self._make_parser(base_url="http://localhost:11434/v1")
        assert str(parser._openai_client.base_url).startswith(
            "http://localhost:11434/v1"
        )

    async def test_parse_returns_episode_dict(self):
        parser = self._make_parser(model="gpt-4o-mini")
        stub_resp = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(parsed=Episode(**EPISODE_DICT)))
            ]
        )
        mock_create = AsyncMock(return_value=stub_resp)
        parser._openai_client.beta.chat.completions.parse = mock_create  # type: ignore[method-assign]

        result = await parser.parse(RAW_TITLE)

        assert result == EPISODE_DICT
        assert mock_create.await_args is not None
        kwargs = mock_create.await_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["messages"][0] == {"role": "system", "content": DEFAULT_PROMPT}
        assert kwargs["messages"][1] == {"role": "user", "content": RAW_TITLE}

    async def test_parse_api_error_returns_none(self):
        parser = self._make_parser()
        parser._openai_client.beta.chat.completions.parse = AsyncMock(  # type: ignore[method-assign]
            side_effect=openai_sdk.APIConnectionError(
                request=httpx.Request("POST", "https://api.openai.com/v1")
            )
        )
        assert await parser.parse(RAW_TITLE) is None

    async def test_parse_empty_parsed_content_returns_none(self):
        parser = self._make_parser()
        stub_resp = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=None))]
        )
        parser._openai_client.beta.chat.completions.parse = AsyncMock(  # type: ignore[method-assign]
            return_value=stub_resp
        )
        assert await parser.parse(RAW_TITLE) is None


class TestAnthropicProvider:
    def _make_parser(self) -> LLMParser:
        return LLMParser(
            api_key="sk-ant-test", provider="anthropic", model="claude-opus-4-8"
        )

    @staticmethod
    def _stub_response(stop_reason: str, text: str):
        return SimpleNamespace(
            stop_reason=stop_reason,
            content=[SimpleNamespace(type="text", text=text)],
        )

    async def test_parse_returns_episode_dict(self):
        parser = self._make_parser()
        mock_create = AsyncMock(
            return_value=self._stub_response("end_turn", json.dumps(EPISODE_DICT))
        )
        parser._anthropic_client.messages.create = mock_create  # type: ignore[method-assign]

        result = await parser.parse(RAW_TITLE)

        assert result == EPISODE_DICT
        assert mock_create.await_args is not None
        kwargs = mock_create.await_args.kwargs
        assert kwargs["model"] == "claude-opus-4-8"
        assert kwargs["system"] == DEFAULT_PROMPT
        assert kwargs["messages"] == [{"role": "user", "content": RAW_TITLE}]
        assert kwargs["output_config"] == {
            "format": {"type": "json_schema", "schema": EPISODE_JSON_SCHEMA}
        }

    async def test_parse_refusal_returns_none(self):
        parser = self._make_parser()
        parser._anthropic_client.messages.create = AsyncMock(  # type: ignore[method-assign]
            return_value=self._stub_response("refusal", "")
        )
        assert await parser.parse(RAW_TITLE) is None

    async def test_parse_api_error_returns_none(self):
        parser = self._make_parser()
        parser._anthropic_client.messages.create = AsyncMock(  # type: ignore[method-assign]
            side_effect=anthropic.APIConnectionError(
                request=httpx.Request("POST", "https://api.anthropic.com")
            )
        )
        assert await parser.parse(RAW_TITLE) is None

    async def test_parse_rate_limit_returns_none(self):
        parser = self._make_parser()
        response = httpx.Response(
            status_code=429,
            request=httpx.Request("POST", "https://api.anthropic.com"),
        )
        parser._anthropic_client.messages.create = AsyncMock(  # type: ignore[method-assign]
            side_effect=anthropic.RateLimitError(
                "rate limited", response=response, body=None
            )
        )
        assert await parser.parse(RAW_TITLE) is None

    async def test_parse_invalid_json_returns_none(self):
        parser = self._make_parser()
        parser._anthropic_client.messages.create = AsyncMock(  # type: ignore[method-assign]
            return_value=self._stub_response("end_turn", "not json at all")
        )
        assert await parser.parse(RAW_TITLE) is None


class TestGeminiProvider:
    def _make_parser(self) -> LLMParser:
        return LLMParser(
            api_key="AIza-test", provider="gemini", model="gemini-2.5-flash"
        )

    async def test_parse_returns_episode_dict(self):
        parser = self._make_parser()
        mock_generate = AsyncMock(
            return_value=SimpleNamespace(text=json.dumps(EPISODE_DICT))
        )
        parser._gemini_client.aio.models.generate_content = mock_generate  # type: ignore[method-assign]

        result = await parser.parse(RAW_TITLE)

        assert result == EPISODE_DICT
        assert mock_generate.await_args is not None
        kwargs = mock_generate.await_args.kwargs
        assert kwargs["model"] == "gemini-2.5-flash"
        assert RAW_TITLE in kwargs["contents"]
        assert kwargs["config"].response_mime_type == "application/json"

    async def test_parse_api_error_returns_none(self):
        parser = self._make_parser()
        parser._gemini_client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
            side_effect=genai_errors.APIError(429, {"error": {"message": "quota"}})
        )
        assert await parser.parse(RAW_TITLE) is None

    async def test_parse_empty_text_returns_none(self):
        parser = self._make_parser()
        parser._gemini_client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
            return_value=SimpleNamespace(text=None)
        )
        assert await parser.parse(RAW_TITLE) is None

    async def test_parse_invalid_json_returns_none(self):
        parser = self._make_parser()
        parser._gemini_client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
            return_value=SimpleNamespace(text="not json")
        )
        assert await parser.parse(RAW_TITLE) is None
