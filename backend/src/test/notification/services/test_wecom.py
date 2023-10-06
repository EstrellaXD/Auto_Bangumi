from unittest import mock

import pytest
from aioresponses import aioresponses
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

    @pytest.mark.asyncio
    async def test__send(self, fake_notification):
        # Create a mock response for the HTTP request
        with aioresponses() as m:
            m.post("https://qyapi.weixin.qq.com/cgi-bin/message/send")

            data = WecomMessage(
                agentid=self.agentid,
                articles=[
                    WecomArticle(
                        title="Test Title",
                        description="<formatted message>",
                        picurl="https://example.com/image.jpg",
                    )
                ],
            )

            # Call the send method
            await self.wecom._send(data.dict())

            m.assert_called_once_with(
                "/cgi-bin/message/send",
                method="POST",
                data=data.dict(),
                params={"access_token": "YOUR_TOKEN"},
            )

    def test_send(self, fake_notification):
        with mock.patch("module.notification.services.wecom.WecomService.send") as m:
            return_value = {"errcode": 0, "errmsg": "ok"}
            m.return_value = return_value

            res = self.wecom.send(fake_notification)

            m.assert_called_with(fake_notification)
            assert res == return_value

    def test_send_failed(self, fake_notification):
        with mock.patch("module.notification.services.wecom.WecomService.send") as m:
            m.return_value = None
            res = self.wecom.send(fake_notification)

            assert res is None
