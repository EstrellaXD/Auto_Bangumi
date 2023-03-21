from module.network import RequestContent
from module.conf import settings


API_URL = "https://openai.estrella.cloud"


class OpenAIParser:
    def __init__(self):
        pass

    def parse(self, title: str) -> dict:
        prompt = {
            "prompt": "This is a test prompt",
        }
        with RequestContent() as req:
            req.get_json(API_URL, params=prompt)
