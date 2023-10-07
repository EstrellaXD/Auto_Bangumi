import logging
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from main import app
from module.models.bangumi import Notification
from module.notification.base import DEFAULT_LOG_TEMPLATE, DEFAULT_MESSAGE_TEMPLATE


@pytest.fixture
def fake_notification():
    yield Notification(
        official_title="AutoBangumi Test",
        season=1,
        episode=1,
        poster_path="https://test.com",
    )


@pytest.fixture
def fake_notification_message(fake_notification):
    return DEFAULT_MESSAGE_TEMPLATE.format(**fake_notification.dict())


@pytest.fixture
def fake_log_record():
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        levelname=logging.getLevelName(logging.INFO),
        msg="test message",
        lineno=1,
        pathname="test.py",
        exc_info=None,
        args=None,
    )


@pytest.fixture
def fake_log_message(fake_log_record) -> str:
    return DEFAULT_LOG_TEMPLATE.format(
        dt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        levelname=fake_log_record.levelname,
        msg=fake_log_record.msg,
    )


@pytest_asyncio.fixture
async def aclient():
    async with AsyncClient(app=app, base_url="http://localhost:7892/api") as client:
        yield client
