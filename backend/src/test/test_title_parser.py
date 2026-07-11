from types import SimpleNamespace
from typing import Literal
from unittest.mock import AsyncMock, patch

import pytest

from module.conf import settings
from module.models import Bangumi, Movie
from module.models.bangumi import Episode
from module.models.config import LLM, ExperimentalOpenAI
from module.parser import title_parser as title_parser_module
from module.parser.analyser.tokenizer import ParseOutcome, ParseTrace
from module.parser.title_parser import TitleParser, _llm_config

RAW_TITLE = (
    "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
)


def _make_llm_episode(episode_type: str = "episode") -> Episode:
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
        episode_type=episode_type,
    )


def _empty_parse_outcome(raw: str = "") -> ParseOutcome:
    return ParseOutcome(result=None, trace=ParseTrace(raw=raw, normalized=raw))


class TestTitleParser:
    async def test_parse_without_llm(self):
        result = await TitleParser.raw_parser(RAW_TITLE)
        assert result is not None
        assert isinstance(result, Bangumi)
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
        assert isinstance(result, Bangumi)
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
                "module.parser.title_parser.parse_release_title_with_trace",
                return_value=_empty_parse_outcome(),
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
            with patch(
                "module.parser.title_parser.parse_release_title_with_trace",
                return_value=_empty_parse_outcome(),
            ):
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

    async def test_llm_keeps_primary_titles_and_reads_deterministic_hints(self):
        """LLM 标题优先，同时确定性解析仍提供安全的结构提示。"""
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(),
            ) as mock_llm:
                with patch(
                    "module.parser.title_parser.parse_release_title_with_trace",
                    return_value=_empty_parse_outcome(),
                ) as mock_raw:
                    result = await TitleParser.raw_parser(RAW_TITLE)

        mock_llm.assert_awaited_once()
        mock_raw.assert_called_once_with(RAW_TITLE)
        assert result is not None
        assert result.official_title == "LLM Title"

    async def test_raw_non_episodic_type_overrides_llm_episode_type(self):
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(episode_type="episode"),
            ):
                result = await TitleParser.raw_parser("[Group] LLM Title Movie [1080P]")

        assert result is not None
        assert isinstance(result, Movie)

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
                with patch(
                    "module.parser.title_parser.parse_release_title_with_trace",
                    return_value=_empty_parse_outcome(),
                ):
                    result = await TitleParser.raw_parser("unparseable garbage title")

        assert result is None


class TestParsedReleaseAdmission:
    """Generic parsing and database admission stay separate and typed."""

    @pytest.mark.parametrize("marker", ("OVA01", "OAD01", "SP01"))
    async def test_numbered_special_projects_to_special_bangumi(self, marker: str):
        with patch.object(settings, "llm", LLM(enable=False)):
            result = await TitleParser.raw_parser(
                f"[Group] Anime Title {marker} [1080p WEB-DL]"
            )

        assert isinstance(result, Bangumi)
        assert result.season == 0
        assert result.episode_type == "special"

    @pytest.mark.parametrize("marker", ("OVA", "OAD", "SP"))
    async def test_unnumbered_special_projects_without_episode_sentinel(
        self, marker: str
    ):
        with patch.object(settings, "llm", LLM(enable=False)):
            result = await TitleParser.raw_parser(
                f"[Group] Anime Title {marker} [1080p WEB-DL]"
            )

        assert isinstance(result, Bangumi)
        assert result.season == 0
        assert result.episode_type == "special"

    async def test_half_episode_projects_without_integer_coercion(self):
        with patch.object(settings, "llm", LLM(enable=False)):
            result = await TitleParser.raw_parser(
                "[Group] Anime Title - 12.5 [1080p WEB-DL]"
            )

        assert isinstance(result, Bangumi)
        assert result.eps_collect is False

    async def test_deterministic_movie_projects_to_movie_and_keeps_year(self):
        with patch.object(settings, "llm", LLM(enable=False)):
            result = await TitleParser.raw_parser(
                "[Group] 劇場版 Anime Title 2024 [1080p BluRay]"
            )

        assert isinstance(result, Movie)
        assert result.year == 2024

    @pytest.mark.parametrize(
        "raw",
        (
            "[Group] Anime Title [01-12] [1080p]",
            "[Group] Anime Title Complete Batch [1080p]",
            "[Group] Anime Title 全集 [1080p]",
            "[Group] Anime Title PV2 [1080p]",
            "[Group] Anime Title NCOP [1080p]",
            "[Group] Anime Title NCED [1080p]",
        ),
    )
    async def test_recognized_non_single_or_auxiliary_video_is_not_persisted(
        self, raw: str
    ):
        with patch.object(settings, "llm", LLM(enable=False)):
            assert await TitleParser.raw_parser(raw) is None

    async def test_strong_title_only_release_is_admitted_but_bare_title_is_not(self):
        with patch.object(settings, "llm", LLM(enable=False)):
            strong = await TitleParser.raw_parser(
                "[Group] Plain Anime Title [1080p WEB-DL]"
            )
            weak = await TitleParser.raw_parser("Plain Anime Title")

        assert isinstance(strong, Bangumi)
        assert weak is None

    async def test_llm_movie_uses_same_movie_projection_as_deterministic_path(self):
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(episode_type="movie"),
            ):
                result = await TitleParser.raw_parser("Opaque LLM Movie Title")

        assert isinstance(result, Movie)

    async def test_primary_llm_cannot_override_explicit_episode_from_movie_group(self):
        raw = "[Movie-Fan] Ordinary Anime - 01 [1080p WEB-DL]"
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(episode_type="movie"),
            ):
                result = await TitleParser.raw_parser(raw)

        assert isinstance(result, Bangumi)
        assert result.episode_type == "episode"

    async def test_deterministic_episode_bundle_stays_atomic_in_primary_mode(self):
        raw = "[Group] Anime Title S02E12v2 [1080p WEB-DL]"
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(),
            ):
                result = await TitleParser.raw_parser(raw)

        assert isinstance(result, Bangumi)
        assert result.season == 2
        assert result.eps_collect is False

    async def test_deterministic_ova_beats_wrong_llm_movie_type(self):
        raw = "[Group] Anime Title OVA [1080p WEB-DL]"
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(episode_type="movie"),
            ):
                result = await TitleParser.raw_parser(raw)

        assert isinstance(result, Bangumi)
        assert result.season == 0
        assert result.episode_type == "special"

    @pytest.mark.parametrize(
        "raw",
        (
            "[Group] Anime Title [01-12] [1080p]",
            "[Group] Anime Title PV2 [1080p]",
            "[Group] Anime Title Complete Batch [1080p]",
            "[Group] Anime Title 合集 [1080p]",
        ),
    )
    async def test_primary_llm_cannot_bypass_deterministic_admission(self, raw: str):
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="primary")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(),
            ):
                result = await TitleParser.raw_parser(raw)

        assert result is None

    async def test_fallback_does_not_call_llm_for_known_rejected_kind(self):
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="fallback")
        ):
            with patch(
                "module.parser.title_parser._llm_parse", new_callable=AsyncMock
            ) as mock_llm:
                result = await TitleParser.raw_parser("[Group] Anime Title PV2 [1080p]")

        assert result is None
        mock_llm.assert_not_awaited()

    @pytest.mark.parametrize("mode", ("primary", "fallback"))
    @pytest.mark.parametrize(
        "raw",
        (
            "[Group] PV [1080p]",
            "[Group] [01-12] [1080p]",
            "[Group] OVA [1080p]",
        ),
    )
    async def test_titleless_structured_resource_never_reaches_llm(
        self, mode: Literal["primary", "fallback"], raw: str
    ):
        with patch.object(settings, "llm", LLM(enable=True, api_key="k", mode=mode)):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(),
            ) as mock_llm:
                result = await TitleParser.raw_parser(raw)

        assert result is None
        mock_llm.assert_not_awaited()

    async def test_real_weak_title_uses_llm_fallback(self):
        with patch.object(
            settings, "llm", LLM(enable=True, api_key="k", mode="fallback")
        ):
            with patch(
                "module.parser.title_parser._llm_parse",
                new_callable=AsyncMock,
                return_value=_make_llm_episode(),
            ) as mock_llm:
                result = await TitleParser.raw_parser("Bare Weak Anime Title")

        assert isinstance(result, Bangumi)
        mock_llm.assert_awaited_once()


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

    async def test_llm_success_is_cached(self):
        mock_parser = AsyncMock()
        mock_parser.parse = AsyncMock(
            return_value={
                "title_en": "Cached",
                "title_zh": None,
                "title_jp": None,
                "season": 1,
                "season_raw": "S1",
                "episode": 1,
                "sub": "",
                "group": "",
                "resolution": "",
                "source": "",
            }
        )
        with patch.object(settings, "llm", LLM(enable=True, api_key="k", cache_ttl=60)):
            with patch(
                "module.parser.title_parser._get_llm_parser", return_value=mock_parser
            ):
                first = await title_parser_module._llm_parse("cached title")
                second = await title_parser_module._llm_parse("cached title")

        assert first == second
        assert mock_parser.parse.await_count == 1

    async def test_llm_failures_are_cached(self):
        mock_parser = AsyncMock()
        mock_parser.parse = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(
            settings,
            "llm",
            LLM(
                enable=True,
                api_key="k",
                cache_ttl=60,
                failure_threshold=10,
            ),
        ):
            with patch(
                "module.parser.title_parser._get_llm_parser", return_value=mock_parser
            ):
                first = await title_parser_module._llm_parse("bad title")
                second = await title_parser_module._llm_parse("bad title")

        assert first is None
        assert second is None
        assert mock_parser.parse.await_count == 1

    async def test_llm_failure_breaker_skips_provider_calls(self):
        mock_parser = AsyncMock()
        mock_parser.parse = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(
            settings,
            "llm",
            LLM(
                enable=True,
                api_key="k",
                cache_ttl=0,
                failure_threshold=2,
                failure_backoff=60,
            ),
        ):
            with patch(
                "module.parser.title_parser._get_llm_parser", return_value=mock_parser
            ):
                assert await title_parser_module._llm_parse("bad title 1") is None
                assert await title_parser_module._llm_parse("bad title 2") is None
                assert await title_parser_module._llm_parse("bad title 3") is None

        assert mock_parser.parse.await_count == 2


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
        title_parser_module._llm_cache = {("old",): (1, None)}
        title_parser_module._llm_failure_count = 2
        title_parser_module._llm_breaker_until = 999

        title_parser_module.reset_cache()

        assert title_parser_module._llm_parser is None
        assert title_parser_module._llm_parser_kwargs is None
        assert title_parser_module._llm_cache == {}
        assert title_parser_module._llm_failure_count == 0
        assert title_parser_module._llm_breaker_until == 0.0
