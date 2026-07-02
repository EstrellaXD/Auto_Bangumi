from unittest.mock import AsyncMock, patch

import pytest

from module.conf import settings
from module.parser import title_parser as title_parser_module
from module.parser.title_parser import TitleParser


class TestTitleParser:
    async def test_parse_without_openai(self):
        text = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
        result = await TitleParser.raw_parser(text)
        assert result is not None
        assert result.group_name == "梦蓝字幕组"
        assert result.title_raw == "New Doraemon"
        assert result.dpi == "1080P"
        assert result.season == 1
        assert result.subtitle == "GB_JP"

    @pytest.mark.skipif(
        not settings.experimental_openai.enable,
        reason="OpenAI is not enabled in settings",
    )
    async def test_parse_with_openai(self):
        text = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
        result = await TitleParser.raw_parser(text)
        assert result is not None
        assert result.group_name == "梦蓝字幕组"
        assert result.title_raw == "New Doraemon"
        assert result.dpi == "1080P"
        assert result.season == 1
        assert result.subtitle == "GB_JP"


class TestRawParserOpenAIFallback:
    """OpenAI is only consulted as a rescue when the regex raw_parser fails,
    never as a replacement for it (see title_parser.py:76-84)."""

    def teardown_method(self):
        title_parser_module.reset_cache()

    def _make_episode_dict(self) -> dict:
        return {
            "title_en": "OpenAI Title",
            "title_zh": None,
            "title_jp": None,
            "season": 1,
            "season_raw": "S1",
            "episode": 1,
            "sub": "GB",
            "group": "OpenAIGroup",
            "resolution": "1080P",
            "source": "Web",
        }

    async def test_raw_parser_regex_success_openai_enabled_skips_openai(self):
        """When the regex parser succeeds, OpenAI must not be invoked even
        if it is enabled — the LLM is a fallback, not a replacement."""
        text = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
        with patch.object(settings.experimental_openai, "enable", True):
            with patch(
                "module.parser.title_parser._get_openai_parser"
            ) as mock_get_parser:
                result = await TitleParser.raw_parser(text)

        assert result is not None
        assert result.title_raw == "New Doraemon"
        mock_get_parser.assert_not_called()

    async def test_raw_parser_regex_failure_openai_enabled_falls_back_to_openai(self):
        """When the regex parser returns None and OpenAI is enabled, OpenAI
        is tried as a rescue and its result is used."""
        mock_gpt = AsyncMock()
        mock_gpt.parse = AsyncMock(return_value=self._make_episode_dict())
        with patch.object(settings.experimental_openai, "enable", True):
            with patch(
                "module.parser.title_parser.raw_parser", return_value=None
            ) as mock_raw_parser:
                with patch(
                    "module.parser.title_parser._get_openai_parser",
                    return_value=mock_gpt,
                ) as mock_get_parser:
                    result = await TitleParser.raw_parser("unparseable garbage title")

        mock_raw_parser.assert_called_once()
        mock_get_parser.assert_called_once()
        mock_gpt.parse.assert_awaited_once()
        assert result is not None
        assert result.official_title == "OpenAI Title"
        assert result.group_name == "OpenAIGroup"

    async def test_raw_parser_regex_failure_openai_disabled_returns_none(self):
        """When the regex parser fails and OpenAI is disabled, no fallback
        happens and the method returns None."""
        with patch.object(settings.experimental_openai, "enable", False):
            with patch("module.parser.title_parser.raw_parser", return_value=None):
                with patch(
                    "module.parser.title_parser._get_openai_parser"
                ) as mock_get_parser:
                    result = await TitleParser.raw_parser("unparseable garbage title")

        assert result is None
        mock_get_parser.assert_not_called()


class TestOpenAIParserResetCache:
    """reset_cache() must drop the lazy OpenAI-parser singleton on config
    reload, or a changed api_key/api_base keeps using the old client."""

    def teardown_method(self):
        title_parser_module.reset_cache()

    def test_reset_cache_clears_singleton(self):
        # A cheap non-None sentinel; the test only cares that reset_cache()
        # clears it, not that it's a real OpenAIParser.
        title_parser_module._openai_parser = object()  # type: ignore[assignment]
        title_parser_module._openai_parser_kwargs = {"api_key": "old"}

        title_parser_module.reset_cache()

        assert title_parser_module._openai_parser is None
        assert title_parser_module._openai_parser_kwargs is None
