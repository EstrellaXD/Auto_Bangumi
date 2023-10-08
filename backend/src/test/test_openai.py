import json
from unittest import mock

from module.parser.analyser.openai import DEFAULT_PROMPT, OpenAIParser


class TestOpenAIParser:
    @classmethod
    def setup_class(cls):
        api_key = "testing!"
        cls.parser = OpenAIParser(api_key=api_key)

    def test__prepare_params_with_openai(self):
        text = "hello world"
        expected = dict(
            api_key=self.parser._api_key,
            api_base=self.parser.api_base,
            messages=[
                dict(role="system", content=DEFAULT_PROMPT),
                dict(role="user", content=text),
            ],
            temperature=0,
            model=self.parser.model,
        )

        params = self.parser._prepare_params(text, DEFAULT_PROMPT)
        assert expected == params

    def test__prepare_params_with_azure(self):
        azure_parser = OpenAIParser(
            api_key="aaabbbcc",
            api_base="https://test.openai.azure.com/",
            api_type="azure",
            api_version="2023-05-15",
            deployment_id="gpt-35-turbo",
        )

        text = "hello world"
        expected = dict(
            api_key=azure_parser._api_key,
            api_base=azure_parser.api_base,
            messages=[
                dict(role="system", content=DEFAULT_PROMPT),
                dict(role="user", content=text),
            ],
            temperature=0,
            deployment_id="gpt-35-turbo",
            api_version="2023-05-15",
            api_type="azure",
        )

        params = azure_parser._prepare_params(text, DEFAULT_PROMPT)
        assert expected == params

    def test_parse(self):
        text = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
        expected = {
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

        with mock.patch("module.parser.analyser.OpenAIParser.parse") as mocker:
            mocker.return_value = json.dumps(expected)

            result = self.parser.parse(text=text, asdict=False)
            assert json.loads(result) == expected
