"""通知中心 REST API（/notification/messages*）。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.database import get_db
from module.models import InboxMessage
from module.security.api import get_current_user


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def app(mock_db):
    app = FastAPI()
    app.include_router(v1, prefix="/api")

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture
def authed_client(app):
    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(app):
    return TestClient(app)


def _message(**overrides) -> InboxMessage:
    fields = dict(
        id=1,
        kind="rss_failure",
        severity="error",
        title="RSS 订阅连接异常",
        body="feed down",
        payload='{"rss_name": "Feed", "error": "boom"}',
        dedup_key="rss_failure:u",
        read=False,
        count=3,
        created_at="2026-07-05T10:00:00+00:00",
        updated_at="2026-07-05T12:00:00+00:00",
    )
    fields.update(overrides)
    return InboxMessage(**fields)


@patch("module.security.api.DEV_AUTH_BYPASS", False)
def test_messages_require_auth(unauthed_client):
    assert unauthed_client.get("/api/v1/notification/messages").status_code == 401


def test_list_messages_returns_parsed_payload(authed_client, mock_db):
    mock_db.inbox.list = AsyncMock(return_value=[_message()])
    mock_db.inbox.count_all = AsyncMock(return_value=1)
    mock_db.inbox.unread_count = AsyncMock(return_value=1)

    resp = authed_client.get("/api/v1/notification/messages")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["unread_count"] == 1
    message = data["messages"][0]
    assert message["kind"] == "rss_failure"
    assert message["payload"] == {"rss_name": "Feed", "error": "boom"}
    assert message["count"] == 3


def test_list_messages_passes_query_params(authed_client, mock_db):
    mock_db.inbox.list = AsyncMock(return_value=[])
    mock_db.inbox.count_all = AsyncMock(return_value=0)
    mock_db.inbox.unread_count = AsyncMock(return_value=0)

    resp = authed_client.get(
        "/api/v1/notification/messages?unread_only=true&limit=10&offset=20"
    )

    assert resp.status_code == 200
    mock_db.inbox.list.assert_awaited_once_with(unread_only=True, limit=10, offset=20)


def test_unread_count(authed_client, mock_db):
    mock_db.inbox.unread_count = AsyncMock(return_value=4)

    resp = authed_client.get("/api/v1/notification/messages/unread-count")

    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 4


def test_mark_read_bumps_revision(authed_client, mock_db):
    mock_db.inbox.mark_read = AsyncMock(return_value=True)

    with patch("module.api.notification.bump_inbox_revision") as bump:
        resp = authed_client.post("/api/v1/notification/messages/5/read")

    assert resp.status_code == 200
    mock_db.inbox.mark_read.assert_awaited_once_with(5)
    bump.assert_called_once()


def test_mark_read_unknown_id_returns_404(authed_client, mock_db):
    mock_db.inbox.mark_read = AsyncMock(return_value=False)

    resp = authed_client.post("/api/v1/notification/messages/999/read")

    assert resp.status_code == 404


def test_mark_all_read(authed_client, mock_db):
    mock_db.inbox.mark_all_read = AsyncMock(return_value=2)

    with patch("module.api.notification.bump_inbox_revision") as bump:
        resp = authed_client.post("/api/v1/notification/messages/read-all")

    assert resp.status_code == 200
    bump.assert_called_once()


def test_delete_message(authed_client, mock_db):
    mock_db.inbox.delete = AsyncMock(return_value=True)

    with patch("module.api.notification.bump_inbox_revision") as bump:
        resp = authed_client.delete("/api/v1/notification/messages/5")

    assert resp.status_code == 200
    mock_db.inbox.delete.assert_awaited_once_with(5)
    bump.assert_called_once()


def test_delete_unknown_id_returns_404(authed_client, mock_db):
    mock_db.inbox.delete = AsyncMock(return_value=False)

    resp = authed_client.delete("/api/v1/notification/messages/999")

    assert resp.status_code == 404


def test_clear_all(authed_client, mock_db):
    mock_db.inbox.clear = AsyncMock(return_value=7)

    with patch("module.api.notification.bump_inbox_revision") as bump:
        resp = authed_client.delete("/api/v1/notification/messages")

    assert resp.status_code == 200
    bump.assert_called_once()
