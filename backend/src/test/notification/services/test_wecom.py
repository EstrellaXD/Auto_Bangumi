from unittest import mock

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

        wecom = WecomService(token=self.token, agentid=self.agentid, base_url="")
        assert wecom.base_url == "https://qyapi.weixin.qq.com"

    def test__process_input_with_notification(
        self, fake_notification, fake_notification_message
    ):
        message = self.wecom._process_input(notification=fake_notification)

        assert message.agentid == self.wecom.agentid
        assert message.articles[0].title == "【番剧更新】" + fake_notification.official_title
        assert message.articles[0].description == fake_notification_message
        assert message.articles[0].picurl == fake_notification.poster_path

    def test__process_input_with_log_record(self, fake_log_record, fake_log_message):
        message = self.wecom._process_input(record=fake_log_record)

        assert message.agentid == self.wecom.agentid
        assert message.articles[0].title == "AutoBangumi"
        assert message.articles[0].description == fake_log_message
        assert not message.articles[0].picurl

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
