"""Tests for the Streamable HTTP MCP endpoint wired up in main.create_app."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from module.mcp import security

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Authorization": "Bearer ab_mcp_test",
}


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.startup = AsyncMock()
    ctx.start_tasks = AsyncMock(return_value=None)
    ctx.stop = AsyncMock()
    ctx.plugins.start = AsyncMock()
    ctx.plugins.stop = AsyncMock()
    ctx.first_run_boot = True
    return ctx


@pytest.fixture
def client():
    service = MagicMock()
    service.authenticate_api_token = AsyncMock(
        side_effect=lambda token, scope: object() if token == "ab_mcp_test" else None
    )
    with (
        patch("main.AppContext.build", return_value=_ctx()),
        patch.object(security, "auth_service", service),
        patch.object(security.settings.security, "mcp_whitelist", []),
    ):
        with TestClient(main.create_app()) as client:
            yield client


@pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
def test_initialize(client, path):
    response = client.post(path, json=INITIALIZE, headers=HEADERS)
    assert response.status_code == 200
    assert '"serverInfo":{"name":"autobangumi"' in response.text


def test_tools_list(client):
    message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    response = client.post("/mcp", json=message, headers=HEADERS)
    assert response.status_code == 200
    assert '"name":"list_anime"' in response.text


def test_requires_token(client):
    headers = {**HEADERS, "Authorization": "Bearer wrong"}
    response = client.post("/mcp", json=INITIALIZE, headers=headers)
    assert response.status_code == 403
