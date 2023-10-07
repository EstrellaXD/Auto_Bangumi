from textwrap import dedent

import pytest
from aioresponses import aioresponses
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    DEFAULT_MESSAGE_TEMPLATE,
    NotifierAdapter,
)


def test_default_message_template(fake_notification):
    content = DEFAULT_MESSAGE_TEMPLATE.format(**fake_notification.dict())
    expected = dedent(
        """\
        番剧名称：AutoBangumi Test
        季度：第1季
        更新集数：第1集
        https://mikanani.me
        """
    )

    assert content == expected


def test_default_log_template():
    content = DEFAULT_LOG_TEMPLATE.format(
        dt="2021-08-15 21:58:44,123",
        levelname="INFO",
        msg="test message",
    )
    expected = dedent(
        """\
        日志时间：2021-08-15 21:58:44,123
        日志等级：INFO
        日志消息：test message
        """
    )

    assert content == expected


def test_NotifierAdapter_non_implementation_raised(fake_notification):
    with pytest.raises(NotImplementedError) as exc:
        NotifierAdapter.send(fake_notification)

    assert exc.match("send method is not implemented yet.")
