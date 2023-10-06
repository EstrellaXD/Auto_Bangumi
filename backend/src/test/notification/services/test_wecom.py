import asyncio
from unittest import mock
import aiohttp
from aioresponses import aioresponses
import pytest
from module.notification.base import NotifierAdapter
from module.notification.services.wecom import WecomArticle, WecomMessage, WecomService


class TestWecomArticle:
    def test_WecomArticle(self):
        article = WecomArticle(
            title="Test Title",
            description="Test Description",
            picurl="https://example.com/image.jpg",
        )

        assert article.title == "Test Title"
        assert article.description == "Test Description"
        assert article.picurl == "https://example.com/image.jpg"

    def test_WecomArticle_default_title(self):
        article = WecomArticle(
            description="Test Description", picurl="https://example.com/image.jpg"
        )
        assert article.title == "AutoBangumi"

    def test_WecomArticle_picurl(self):
        article = WecomArticle(
            title="Test Title",
            description="Test Description",
            picurl="https://mikanani.me",
        )
        placeholder_pic = "https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png"
        assert article.picurl == placeholder_pic


class TestWecomMessage:
    def test_WecomMessage(self):
        message = WecomMessage(
            agentid="YOUR_AGENT_ID",
            articles=[
                WecomArticle(
                    title="Test Title",
                    description="<formatted message>",
                    picurl="https://example.com/image.jpg",
                )
            ],
        )

        assert message.msgtype == "news"
        assert message.agentid == "YOUR_AGENT_ID"
        assert message.articles[0].title == "Test Title"
        assert message.articles[0].description == "<formatted message>"
        assert message.articles[0].picurl == "https://example.com/image.jpg"


class TestWecomService:
    def test_WecomService_inherits_NotifierAdapter(self):
        assert issubclass(WecomService, NotifierAdapter)

    @classmethod
    def setup_class(cls):
        cls.token = "YOUR_TOKEN"
        cls.agentid = "YOUR_AGENT_ID"
        cls.base_url = "https://qyapi.weixin.qq.com"
        cls.wecom = WecomService(token=cls.token, agentid=cls.agentid)

    def test_init_properties(self):
        assert self.wecom.token == self.token
        assert self.wecom.agentid == self.agentid
        assert self.wecom.base_url == self.base_url

    # def test__send(self, fake_notification):
    #     # Create a mock response for the HTTP request
    #     mock_response = {"errcode": 0, "errmsg": "ok"}
    #     loop = asyncio.get_event_loop()
    #     with mock.patch("aiohttp.ClientSession.post") as m:
    #         m.post("/send", payload=mock_response, status=200)

    #         data = WecomMessage(
    #             agentid=self.agentid,
    #             articles=[
    #                 WecomArticle(
    #                     title="Test Title",
    #                     description="<formatted message>",
    #                     picurl="https://example.com/image.jpg",
    #                 )
    #             ],
    #         )

    #         # Call the send method
    #         res = loop.run_until_complete(self.wecom._send(data.dict()))
    #         # Assertions
    #         m.assert_called_with(
    #             "/cgi-bin/message/send",
    #             params={"access_token": "YOUR_TOKEN"},
    #             status=200,
    #             data=data.dict(),
    #         )
    #         assert res == mock_response
