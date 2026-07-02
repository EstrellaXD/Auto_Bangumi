import pytest

from module.conf import settings
from module.parser import title_parser as title_parser_module
from module.parser.title_parser import TitleParser


class TestTitleParser:
    async def test_parse_without_openai(self):
        text = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
        result = await TitleParser.raw_parser(text)
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
        assert result.group_name == "梦蓝字幕组"
        assert result.title_raw == "New Doraemon"
        assert result.dpi == "1080P"
        assert result.season == 1
        assert result.subtitle == "GB_JP"


class TestOpenAIParserResetCache:
    """reset_cache() must drop the lazy OpenAI-parser singleton on config
    reload, or a changed api_key/api_base keeps using the old client."""

    def teardown_method(self):
        title_parser_module.reset_cache()

    def test_reset_cache_clears_singleton(self):
        title_parser_module._openai_parser = object()
        title_parser_module._openai_parser_kwargs = {"api_key": "old"}

        title_parser_module.reset_cache()

        assert title_parser_module._openai_parser is None
        assert title_parser_module._openai_parser_kwargs is None
