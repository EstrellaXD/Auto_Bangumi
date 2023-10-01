import json
import os
from unittest import mock

from dotenv import load_dotenv
from module.parser.analyser.openai import OpenAIParser

load_dotenv()


class TestOpenAIParser:
    @classmethod
    def setup_class(cls):
        api_key = os.getenv("OPENAI_API_KEY") or "testing!"
        cls.parser = OpenAIParser(api_key=api_key)

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

        with mock.patch("module.parser.openai.OpenAIParser.parse") as mocker:
            mocker.return_value = json.dumps(expected)

            result = self.parser.parse(text=text, asdict=False)
            assert json.loads(result) == expected
