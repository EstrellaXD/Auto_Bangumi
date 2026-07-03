from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from module.conf import settings
from module.models.bangumi import Episode
from module.models.config import LLM, ExperimentalOpenAI
from module.parser import title_parser as title_parser_module
from module.parser.title_parser import TitleParser, _llm_config

RAW_TITLE = (
    "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
)


def _make_llm_episode() -> Episode:
    return Episode(
        title_en="LLM Title",
        title_zh=None,
        title_jp=None,
        season=1,
        season_raw="S1",
        episode=1,
        sub="GB",
        group="LLMGroup",
        resolution="1080P",
        source="Web",
    )


class TestTitleParser:
    async def test_parse_without_llm(self):
        result = await TitleParser.raw_parser(RAW_TITLE)
        assert result is not None
        assert result.group_name == "梦蓝字幕组"
        assert result.title_raw == "New Doraemon"
        assert result.dpi == "1080P"
        assert result.season == 1
        assert result.subtitle == "GB_JP"

    @pytest.mark.skipif(
        not settings.llm.enable,
        reason="LLM is not enabled in settings",
    )
    async def test_parse_with_llm(self):
        result = await TitleParser.raw_parser(RAW_TITLE)
        assert result is not None
        assert result.group_name == "梦蓝字幕组"
        assert result.title_raw == "New Doraemon"
        assert result.dpi == "1080P"
        assert result.season == 1
        assert result.subtitle == "GB_JP"


class TestRawParserLLMFallbackMode:
    """fallback 模式（默认）：正则优先，LLM 仅在正则失败时兜底。"""

    def teardown_method(self):
        title_parser_module.reset_cache()

    async def test_regex_success_skips_llm(self):
        """正则解析成功时，即使启用了 LLM 也不得调用。"""
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="fallback")
        ):
            with patch(
                "module.parser.title_parser._llm_parse", new_callable=AsyncMock
            ) as mock_llm:
                result = await TitleParser.raw_parser(RAW_TITLE)

        assert result is not None
        assert result.title_raw == "New Doraemon"
        mock_llm.assert_not_awaited()

    async def test_regex_failure_falls_back_to_llm(self):
        """正则失败且启用 LLM 时，LLM 兜底解析并采用其结果。"""
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="fallback")
        ):
            with patch(
                "module.parser.title_parser.raw_parser", return_value=None
            ) as mock_raw:
                with patch(
                    "module.parser.title_parser._llm_parse",
                    new_callable=AsyncMock,
                    return_value=_make_llm_episode(),
                ) as mock_llm:
                    result = await TitleParser.raw_parser("unparseable garbage title")

        mock_raw.assert_called_once()
        mock_llm.assert_awaited_once()
        assert result is not None
        assert result.official_title == "LLM Title"
        assert result.group_name == "LLMGroup"

    async def test_regex_failure_llm_disabled_returns_none(self):
        """正则失败且 LLM 未启用时直接返回 None。"""
        with patch.object(settings, "llm", LLM(enable=False, mode="fallback")):
            with patch("module.parser.title_parser.raw_parser", return_value=None):
                with patch(
                    "module.parser.title_parser._llm_parse", new_callable=AsyncMock
                ) as mock_llm:
                    result = await TitleParser.raw_parser("unparseable garbage title")

        assert result is None
        mock_llm.assert_not_awaited()


class TestRawParserLLMPrimaryMode:
    """primary 模式：LLM 优先解析每个标题，失败时正则兜底，不丢标题。"""

    def teardown_method(self):
        title_parser_module.reset_cache()

    async def test_llm_called_first_and_regex_skipped(self):
        """LLM 成功时结果直接采用，正则解析不再执行。"""
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(),
            ) as mock_llm:
                with patch("module.parser.title_parser.raw_parser") as mock_raw:
                    result = await TitleParser.raw_parser(RAW_TITLE)

        mock_llm.assert_awaited_once()
        mock_raw.assert_not_called()
        assert result is not None
        assert result.official_title == "LLM Title"

    async def test_llm_failure_falls_back_to_regex(self):
        """LLM 失败（返回 None）时用正则兜底，标题不丢失。"""
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_llm:
                result = await TitleParser.raw_parser(RAW_TITLE)

        mock_llm.assert_awaited_once()
        assert result is not None
        assert result.title_raw == "New Doraemon"

    async def test_llm_and_regex_both_fail_returns_none(self):
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch("module.parser.title_parser.raw_parser", return_value=None):
                    result = await TitleParser.raw_parser("unparseable garbage title")

        assert result is None


class TestLLMParseErrorHandling:
    """_llm_parse 对 LLM 异常/坏输出的容错：一律返回 None，不向上抛。"""

    def teardown_method(self):
        title_parser_module.reset_cache()

    async def test_llm_parser_exception_returns_none(self):
        mock_parser = AsyncMock()
        mock_parser.parse = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(settings, "llm", LLM(enable=True, api_key="k")):
            with patch(
                "module.parser.title_parser._get_llm_parser", return_value=mock_parser
            ):
                result = await title_parser_module._llm_parse("some title")
        assert result is None

    async def test_llm_non_dict_result_returns_none(self):
        mock_parser = AsyncMock()
        mock_parser.parse = AsyncMock(return_value=None)
        with patch.object(settings, "llm", LLM(enable=True, api_key="k")):
            with patch(
                "module.parser.title_parser._get_llm_parser", return_value=mock_parser
            ):
                result = await title_parser_module._llm_parse("some title")
        assert result is None


class TestLLMConfigLegacyFallback:
    """llm 段缺失时，_llm_config 回退读取旧的 experimental_openai 段。"""

    def test_legacy_settings_used_when_llm_absent(self):
        legacy_settings = SimpleNamespace(
            experimental_openai=ExperimentalOpenAI(
                enable=True, api_key="sk-legacy", model="gpt-4o"
            )
        )
        with patch("module.parser.title_parser.settings", legacy_settings):
            conf = _llm_config()

        assert conf.enable is True
        assert conf.provider == "openai"
        assert conf.api_key == "sk-legacy"
        assert conf.model == "gpt-4o"
        # 旧配置的语义是 LLM 优先
        assert conf.mode == "primary"

    def test_llm_section_preferred_when_present(self):
        conf = _llm_config()
        assert conf is settings.llm


class TestLLMParserResetCache:
    """reset_cache() must drop the lazy LLM-parser singleton on config
    reload, or a changed api_key/base_url/provider keeps using the old client."""

    def teardown_method(self):
        title_parser_module.reset_cache()

    def test_reset_cache_clears_singleton(self):
        # A cheap non-None sentinel; the test only cares that reset_cache()
        # clears it, not that it's a real LLMParser.
        title_parser_module._llm_parser = object()  # type: ignore[assignment]
        title_parser_module._llm_parser_kwargs = {"api_key": "old"}

        title_parser_module.reset_cache()

        assert title_parser_module._llm_parser is None
        assert title_parser_module._llm_parser_kwargs is None
