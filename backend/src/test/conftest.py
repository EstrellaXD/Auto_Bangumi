import logging
from datetime import datetime, timedelta
from unittest import mock
from fastapi import Cookie
import httpx

import pytest
import pytest_asyncio
from httpx import AsyncClient
from pytest_mock import MockerFixture
from main import app
from module.models.bangumi import Notification
from module.notification.base import (
    DEFAULT_LOG_TEMPLATE,
    DEFAULT_MESSAGE_TEMPLATE,
    NotificationContent,
)
from module.security.api import get_current_user
from module.security.jwt import create_access_token


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


@pytest.fixture
def fake_content():
    return NotificationContent(content="test content")


@pytest.fixture
def fake_token():
    return create_access_token(data={"sub": "test"}, expires_delta=timedelta(days=1))


@pytest_asyncio.fixture
async def aclient(mocker: MockerFixture):
    # mock get_current_user to avoid authorization
    # see: https://github.com/tiangolo/fastapi/issues/3331
    app.dependency_overrides[get_current_user] = lambda: mocker.MagicMock(
        return_value="test"
    )

    async with AsyncClient(app=app, base_url="http://localhost:7892/api") as client:
        yield client

    app.dependency_overrides.clear()
